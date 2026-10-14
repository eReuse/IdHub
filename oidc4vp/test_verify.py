"""The Verifier side: the two endpoints a peer instance talks to.

``/oidc4vp/verify`` is machine to machine and csrf exempt, authenticated with
HTTP Basic against the ``client_id``/``client_secret`` pair the peer was given:
``GET`` starts a verification and ``POST`` receives the presentation.
``/oidc4vp/allow_code`` is where the browser lands afterwards, carrying the
code, and is the only part of the flow a person sees.

Nothing here is reachable with a login, so every refusal is a 404 on purpose:
the endpoint does not admit that an organization exists.
"""
import base64
import binascii
import json
import logging

from unittest.mock import Mock, patch

from django.core import mail
from django.test import override_settings
from django.urls import reverse

from oidc4vp.models import Authorization, OAuth2VPToken, Organization
from promotion.models import Promotion
from test_support import factories
from test_support.base import IdHubTestCase


def basic(client_id, client_secret):
    token = base64.b64encode(
        '{}:{}'.format(client_id, client_secret).encode()
    ).decode()
    return {'authorization': 'Basic {}'.format(token)}


class VerifierTestCase(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.peer = Organization.objects.create(
            name='Peer',
            response_uri='https://peer.example.org/oidc4vp/',
            my_client_id='my-client-id',
            my_client_secret='my-client-secret',
        )
        self.auth = basic(self.peer.client_id, self.peer.client_secret)
        # With ENABLE_EMAIL off, send_email() writes the whole notification
        # through logger.warning, and the logger has no handler of its own: it
        # would reach stderr and bury the output of the suite.
        logger = logging.getLogger('oidc4vp.views')
        logger.addHandler(logging.NullHandler())
        logger.propagate = False
        self.addCleanup(setattr, logger, 'propagate', True)
        self.addCleanup(logger.handlers.clear)

    def presentation(self, code):
        credential = factories.make_issued_credential(self.user)
        return factories.make_presentation(self.user, [credential], code=code)


class ValidateTest(VerifierTestCase):
    """The Basic authentication both methods share."""

    def test_a_request_without_credentials_is_not_found(self):
        self.assertEqual(self.client.get(reverse('oidc4vp:verify')).status_code, 404)

    def test_a_known_peer_is_let_in(self):
        self.assertEqual(
            self.client.get(reverse('oidc4vp:verify'), headers=self.auth).status_code,
            200,
        )

    def test_the_secret_has_to_match_too(self):
        response = self.client.get(
            reverse('oidc4vp:verify'),
            headers=basic(self.peer.client_id, 'not-the-secret'),
        )

        self.assertEqual(response.status_code, 404)

    def test_the_credentials_we_use_to_call_them_are_not_accepted(self):
        response = self.client.get(
            reverse('oidc4vp:verify'),
            headers=basic(self.peer.my_client_id, self.peer.my_client_secret),
        )

        self.assertEqual(response.status_code, 404)

    def test_another_authentication_scheme_is_not_found(self):
        for header in ('Bearer sometoken', 'Basic', 'Basic a b', ''):
            with self.subTest(header=header):
                response = self.client.get(
                    reverse('oidc4vp:verify'),
                    headers={'authorization': header},
                )
                self.assertEqual(response.status_code, 404)

    def test_the_scheme_is_matched_case_insensitively(self):
        header = dict(self.auth)
        header['authorization'] = header['authorization'].replace('Basic', 'basic')

        self.assertEqual(
            self.client.get(reverse('oidc4vp:verify'), headers=header).status_code,
            200,
        )

    def test_a_token_that_is_not_base64_is_a_crash_and_not_a_404(self):
        # assertLogs keeps the traceback Django reports for the 500 out of the
        # output of the suite.
        with self.assertRaises(binascii.Error), self.assertLogs('django.request'):
            self.client.get(
                reverse('oidc4vp:verify'),
                headers={'authorization': 'Basic not-base-64-at-all'},
            )

    def test_a_token_without_a_colon_is_a_crash_and_not_a_404(self):
        token = base64.b64encode(b'no-colon-here').decode()

        with self.assertRaises(ValueError), self.assertLogs('django.request'):
            self.client.get(
                reverse('oidc4vp:verify'),
                headers={'authorization': 'Basic {}'.format(token)},
            )


class DemandAuthorizationTest(VerifierTestCase):
    """``GET /oidc4vp/verify``: the peer asks us to start a verification."""

    def get(self):
        return self.client.get(reverse('oidc4vp:verify'), headers=self.auth)

    def test_an_authorization_is_created_for_the_peer(self):
        self.get()

        authorization = Authorization.objects.get()
        self.assertEqual(authorization.organization, self.peer)
        self.assertFalse(authorization.code_used)

    @override_settings(SUPPORTED_CREDENTIALS=['MembershipCard'])
    def test_what_we_ask_for_is_the_configured_credential_list(self):
        self.get()

        self.assertEqual(
            json.loads(Authorization.objects.get().presentation_definition),
            ['MembershipCard'],
        )

    def test_the_answer_is_the_url_to_redirect_the_holder_to(self):
        payload = json.loads(self.get().content)

        authorization = Authorization.objects.get()
        self.assertTrue(
            payload['redirect_uri'].startswith(
                'https://peer.example.org/oidc4vp/authorize?'
            ),
            payload['redirect_uri'],
        )
        self.assertIn('code={}'.format(authorization.code), payload['redirect_uri'])

    def test_the_holder_is_sent_back_to_the_peer_and_not_to_us(self):
        # The url is built from the peer's response_uri, so this instance is
        # only the Verifier of record: the wallet dialog happens over there.
        payload = json.loads(self.get().content)

        self.assertNotIn('testserver', payload['redirect_uri'])

    def test_every_call_starts_a_new_authorization(self):
        self.get()
        self.get()

        self.assertEqual(Authorization.objects.count(), 2)
        self.assertEqual(
            Authorization.objects.values_list('code', flat=True).distinct().count(),
            2,
        )


class ReceivePresentationTest(VerifierTestCase):
    """``POST /oidc4vp/verify``: the presentation comes back."""

    def setUp(self):
        super().setUp()
        self.authorization = Authorization.objects.create(
            organization=self.peer,
            presentation_definition=json.dumps(['MembershipCard']),
        )

    def post(self, **data):
        return self.client.post(
            reverse('oidc4vp:verify'), data, headers=self.auth
        )

    def test_a_request_missing_either_field_is_not_found(self):
        for data in (
            {},
            {'code': 'a-code'},
            {'vp_token': '<the vp>'},
        ):
            with self.subTest(data=data):
                self.assertEqual(self.post(**data).status_code, 404)

    def test_an_unknown_code_is_not_found(self):
        response = self.post(vp_token='<the vp>', code='not-a-known-code')

        self.assertEqual(response.status_code, 404)
        self.assertFalse(OAuth2VPToken.objects.exists())

    def test_the_request_is_refused_before_the_code_is_looked_up(self):
        response = self.client.post(
            reverse('oidc4vp:verify'),
            {'vp_token': '<the vp>', 'code': self.authorization.code},
        )

        self.assertEqual(response.status_code, 404)

    def test_a_valid_presentation_is_accepted_and_stored(self):
        vp = self.presentation(self.authorization.code)

        payload = json.loads(self.post(vp_token=vp, code=self.authorization.code).content)

        self.assertEqual(payload['verify'], 'Ok, Correct verification')
        self.assertEqual(
            payload['response'], 'Validation Code {}'.format(self.authorization.code)
        )
        self.assertEqual(OAuth2VPToken.objects.get().vp_token, vp)

    def test_the_holder_is_not_recorded_anywhere(self):
        # The user column stays empty: the Verifier knows the credential and
        # the code, not which account on the peer sent them.
        vp = self.presentation(self.authorization.code)
        self.post(vp_token=vp, code=self.authorization.code)

        self.assertIsNone(OAuth2VPToken.objects.get().user)
        self.assertEqual(OAuth2VPToken.objects.get().organization, self.peer)

    def test_a_tampered_presentation_is_rejected(self):
        vp = json.loads(self.presentation(self.authorization.code))
        vp['holder'] = 'did:key:z6MkjchhfUsD6mmvni8mCdXHw216Xrm9bQe2mBH1P5RDjVJG'

        payload = json.loads(
            self.post(vp_token=json.dumps(vp), code=self.authorization.code).content
        )

        self.assertEqual(payload['verify'], 'Error, Failed verification')

    def test_a_presentation_that_is_not_json_crashes(self):
        with self.assertRaises(json.JSONDecodeError), \
                self.assertLogs('django.request'):
            self.post(vp_token='not json at all', code=self.authorization.code)

    def test_the_code_is_still_not_marked_as_used(self):
        # Nothing in the project ever writes code_used, so the same code can
        # be presented against as many times as the peer likes.
        vp = self.presentation(self.authorization.code)
        self.post(vp_token=vp, code=self.authorization.code)
        self.post(vp_token=vp, code=self.authorization.code)

        self.authorization.refresh_from_db()
        self.assertFalse(self.authorization.code_used)
        self.assertEqual(OAuth2VPToken.objects.count(), 2)

    @override_settings(
        OIDC_REDIRECT=True, ALLOW_CODE_URI='https://testserver/oidc4vp/allow_code'
    )
    def test_with_the_redirection_on_the_answer_carries_the_allow_code_url(self):
        vp = self.presentation(self.authorization.code)

        payload = json.loads(
            self.post(vp_token=vp, code=self.authorization.code).content
        )

        self.assertEqual(
            payload['redirect_uri'],
            'https://testserver/oidc4vp/allow_code?code={}'.format(
                self.authorization.code
            ),
        )

    @override_settings(OIDC_REDIRECT=False)
    def test_with_the_redirection_off_there_is_nowhere_to_send_the_browser(self):
        vp = self.presentation(self.authorization.code)

        payload = json.loads(
            self.post(vp_token=vp, code=self.authorization.code).content
        )

        self.assertEqual(payload['redirect_uri'], '')


class VerificationEmailTest(VerifierTestCase):
    def setUp(self):
        super().setUp()
        self.authorization = Authorization.objects.create(
            organization=self.peer,
            presentation_definition=json.dumps(['MembershipCard']),
        )
        self.vp = self.presentation(self.authorization.code)

    def post(self, vp_token=None):
        return self.client.post(
            reverse('oidc4vp:verify'),
            {'vp_token': vp_token or self.vp, 'code': self.authorization.code},
            headers=self.auth,
        )

    @override_settings(ENABLE_EMAIL=True)
    def test_every_admin_is_told_about_a_verification(self):
        factories.make_user('second@example.org', 'secondpass12', admin=True)

        self.post()

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            sorted(sum((m.to for m in mail.outbox), [])),
            [self.ADMIN_EMAIL, 'second@example.org'],
        )

    @override_settings(ENABLE_EMAIL=True)
    def test_the_email_carries_the_code_and_the_presented_data(self):
        self.post()

        body = mail.outbox[0].body
        self.assertIn(self.authorization.code, body)
        self.assertIn(self.user.email, body)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)

    @override_settings(ENABLE_EMAIL=True)
    def test_a_failed_verification_is_not_worth_an_email(self):
        vp = json.loads(self.vp)
        vp['holder'] = 'did:key:z6MkjchhfUsD6mmvni8mCdXHw216Xrm9bQe2mBH1P5RDjVJG'

        self.post(vp_token=json.dumps(vp))

        self.assertEqual(mail.outbox, [])

    @override_settings(ENABLE_EMAIL=False)
    def test_with_email_disabled_the_verification_is_only_logged(self):
        with self.assertLogs('oidc4vp.views', level='WARNING') as logs:
            self.post()

        self.assertEqual(mail.outbox, [])
        self.assertIn(self.ADMIN_EMAIL, logs.output[0])

    @override_settings(ENABLE_EMAIL=True)
    def test_a_broken_mail_server_does_not_lose_the_verification(self):
        with patch('oidc4vp.views.EmailMultiAlternatives.send', side_effect=OSError):
            response = self.post()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(OAuth2VPToken.objects.count(), 1)


class AllowCodeTest(IdHubTestCase):
    """Where the browser lands with the code once the wallet answered."""

    def setUp(self):
        super().setUp()
        self.authorization = Authorization.objects.create(
            presentation_definition=json.dumps(['MembershipCard'])
        )
        patcher = patch('oidc4vp.views.requests')
        self.requests = patcher.start()
        self.addCleanup(patcher.stop)

    def url(self, code=None):
        code = self.authorization.code if code is None else code
        return '{}?code={}'.format(reverse('oidc4vp:allow_code'), code)

    def add_vp_token(self):
        token = OAuth2VPToken(
            vp_token=json.dumps({'holder': 'did:key:z6MkpEZ'}),
            code=self.authorization.code,
        )
        token.save()
        return token

    def set_response_uri(self, url='https://peer.example.org/oidc4vp/verify'):
        session = self.client.session
        session['response_uri'] = url
        session.save()

    def test_without_a_code_there_is_nothing_to_allow(self):
        self.assertEqual(
            self.client.get(reverse('oidc4vp:allow_code')).status_code, 404
        )

    def test_an_unknown_code_is_not_found(self):
        self.assertEqual(self.client.get(self.url('not-a-code')).status_code, 404)

    def test_a_code_already_marked_as_used_is_not_found(self):
        self.authorization.code_used = True
        self.authorization.save()

        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_the_same_code_can_be_allowed_twice(self):
        # Which is the practical consequence of nothing ever setting
        # code_used: the guard above is unreachable through the application.
        for _ in range(2):
            self.assertRedirects(
                self.client.get(self.url()),
                reverse('oidc4vp:received_code'),
                fetch_redirect_response=False,
            )

    def test_a_plain_code_ends_on_the_thank_you_page(self):
        self.assertRedirects(
            self.client.get(self.url()),
            reverse('oidc4vp:received_code'),
            fetch_redirect_response=False,
        )

    def test_a_code_tied_to_a_promotion_goes_to_the_contract(self):
        Promotion.objects.create(
            name='Som Connexio',
            discount=Promotion.Types.VULNERABLE,
            authorize=self.authorization,
        )

        self.assertRedirects(
            self.client.get(self.url()),
            '{}?code={}'.format(
                reverse('promotion:contract'), self.authorization.code
            ),
            fetch_redirect_response=False,
        )

    def test_an_api_caller_gets_the_presentation_forwarded(self):
        token = self.add_vp_token()
        self.set_response_uri()
        self.requests.post.return_value = Mock(
            **{'json.return_value': {'redirect_uri': 'https://peer.example.org/ok'}}
        )

        response = self.client.get(self.url())

        self.assertRedirects(
            response, 'https://peer.example.org/ok', fetch_redirect_response=False
        )
        sent = self.requests.post.call_args.kwargs['data']
        self.assertEqual(
            base64.b64decode(sent['vp_token']).decode(), token.vp_token
        )
        self.assertEqual(sent['code'], self.authorization.code)

    def test_without_a_presentation_there_is_nothing_to_forward(self):
        self.set_response_uri()

        self.assertRedirects(
            self.client.get(self.url()),
            reverse('oidc4vp:received_code'),
            fetch_redirect_response=False,
        )
        self.requests.post.assert_not_called()

    def test_an_api_caller_that_answers_nothing_falls_back_to_the_page(self):
        self.add_vp_token()
        self.set_response_uri()
        self.requests.post.return_value = Mock(**{'json.return_value': {}})

        self.assertRedirects(
            self.client.get(self.url()),
            reverse('oidc4vp:received_code'),
            fetch_redirect_response=False,
        )

    def test_the_presentation_forwarded_is_the_first_one_received(self):
        first = self.add_vp_token()
        self.add_vp_token()
        self.set_response_uri()
        self.requests.post.return_value = Mock(**{'json.return_value': {}})

        self.client.get(self.url())

        sent = self.requests.post.call_args.kwargs['data']
        self.assertEqual(
            base64.b64decode(sent['vp_token']).decode(), first.vp_token
        )


class ReceivedCodeTest(IdHubTestCase):
    def test_the_thank_you_page_needs_no_login_and_no_code(self):
        response = self.client.get(reverse('oidc4vp:received_code'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'we are received your presentation correctly',
            response.content.decode(),
        )
