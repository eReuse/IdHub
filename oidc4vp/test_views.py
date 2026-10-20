"""The holder side: choosing a credential and sending it to a Verifier.

``AuthorizeView`` is reached from outside, through the url a Verifier put in
the QR or the redirection: everything that drives it travels in the query
string (``client_id``, ``presentation_definition`` and ``code``), and the
credential to send comes from the posted form.

The outbound POST to the peer is patched at ``oidc4vp.models.requests``, so
the tests describe what the peer answers and what the holder does about it.
"""
import json

from unittest.mock import Mock, patch
from urllib.parse import unquote, urlencode

from django.urls import reverse

from idhub.models import Event, VerificableCredential
from oidc4vp.models import Organization
from test_support import factories
from test_support.base import IdHubTestCase


# What Schemas.get_type makes of the "Membership Card" title: title case with
# the spaces removed. The presentation definition has to use this spelling.
CREDENTIAL_TYPE = 'MembershipCard'
PRESENTATION_DEFINITION = json.dumps([CREDENTIAL_TYPE])
CODE = 'a-code-from-the-verifier'


def peer_answers(status_code=200, **payload):
    response = Mock(status_code=status_code)
    response.json.return_value = payload
    return response


class AuthorizeViewTest(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.verifier = Organization.objects.create(
            name='Verifier',
            response_uri='https://verifier.example.org/oidc4vp/',
            my_client_id='my-client-id',
            my_client_secret='my-client-secret',
        )
        patcher = patch('oidc4vp.models.requests')
        self.requests = patcher.start()
        self.addCleanup(patcher.stop)
        self.requests.post.return_value = peer_answers(
            verify='Ok, Correct verification', redirect_uri='', response=''
        )

    def url(self, **overrides):
        params = {
            'client_id': self.verifier.client_id,
            'presentation_definition': PRESENTATION_DEFINITION,
            'code': CODE,
        }
        params.update(overrides)
        params = {k: v for k, v in params.items() if v is not None}
        return '{}?{}'.format(reverse('oidc4vp:authorize'), urlencode(params))

    def issued_credential(self):
        return factories.make_issued_credential(self.user)

    def enabled_credential(self):
        schema = factories.make_schema('membership-card.json')
        return factories.make_credential(
            self.user, schema, factories.make_did(label='Issuer'),
            factories.MEMBERSHIP_ROW,
        )

    def post_credential(self, credential, **overrides):
        return self.client.post(
            self.url(**overrides), {CREDENTIAL_TYPE.lower(): str(credential.id)}
        )

    # The query string is the whole request

    def test_an_anonymous_visitor_is_sent_to_the_login_page(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 302)
        login_url, next_url = response.url.split('?next=')
        self.assertEqual(login_url, '/login/')
        # The whole request, query string included, so logging in resumes it.
        self.assertEqual(unquote(next_url), self.url())

    def test_without_a_client_id_there_is_no_verifier_to_answer(self):
        self.user_login()

        self.assertEqual(self.client.get(self.url(client_id=None)).status_code, 404)

    def test_an_unknown_client_id_is_not_found(self):
        self.user_login()

        self.assertEqual(
            self.client.get(self.url(client_id='nobody')).status_code, 404
        )

    def test_the_client_id_matched_is_the_one_the_peer_uses_to_reach_us(self):
        self.user_login()
        self.issued_credential()

        response = self.client.get(self.url(client_id=self.verifier.my_client_id))
        self.assertEqual(response.status_code, 404)

    def test_the_requested_credential_is_offered_as_a_radio_choice(self):
        self.user_login()
        credential = self.issued_credential()

        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(
            form.fields[CREDENTIAL_TYPE.lower()].choices,
            [(str(credential.id), CREDENTIAL_TYPE.lower())],
        )

    def test_a_broken_presentation_definition_asks_for_every_credential(self):
        # json.loads fails, the definition becomes [], and the regex built
        # from it is '()', which matches any type: the form then offers no
        # field to choose from, so nothing can be sent.
        self.user_login()
        self.issued_credential()

        response = self.client.get(
            self.url(presentation_definition='not json')
        )

        form = response.context['form']
        self.assertEqual(form.presentation_definition, [])
        self.assertEqual(form.all_credentials.count(), 1)
        self.assertEqual(form.fields, {})

    def test_a_credential_of_another_type_is_not_offered(self):
        self.user_login()
        self.issued_credential()

        response = self.client.get(
            self.url(presentation_definition=json.dumps(['Course Credential']))
        )

        self.assertEqual(response.context['form'].all_credentials.count(), 0)

    def test_a_credential_of_another_user_is_not_offered(self):
        other = factories.make_user('other@example.org', 'otherpass12')
        factories.make_issued_credential(other)
        self.user_login()

        self.assertEqual(
            self.client.get(self.url()).context['form'].all_credentials.count(), 0
        )

    # The detour through the request page

    def test_a_credential_that_is_not_issued_yet_sends_the_user_to_request_it(self):
        self.user_login()
        self.enabled_credential()

        response = self.client.get(self.url())

        self.assertRedirects(
            response, reverse('idhub:user_credentials_request'),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.session['next_url'], self.url())

    def test_the_detour_is_taken_before_anything_is_rendered(self):
        # The url is kept in the session so that CredentialsRequestView can
        # come back to this very request once the credential is issued.
        self.user_login()
        self.enabled_credential()
        self.client.get(self.url())

        self.assertRedirects(
            self.client.get(self.url()),
            reverse('idhub:user_credentials_request'),
            fetch_redirect_response=False,
        )

    # Sending the presentation

    def test_the_presentation_is_posted_to_the_verifier(self):
        self.user_login()
        credential = self.issued_credential()

        self.post_credential(credential)

        url, = self.requests.post.call_args.args
        self.assertEqual(url, 'https://verifier.example.org/oidc4vp/verify')
        sent = self.requests.post.call_args.kwargs['data']
        self.assertEqual(sent['code'], CODE)
        self.assertIn('proof', json.loads(sent['vp_token']))

    def test_the_credential_sent_is_the_one_that_was_chosen(self):
        self.user_login()
        credential = self.issued_credential()

        self.post_credential(credential)

        vp = json.loads(self.requests.post.call_args.kwargs['data']['vp_token'])
        self.assertEqual(
            vp['verifiableCredential'][0]['credentialSubject']['email'],
            self.user.email,
        )
        self.assertEqual(vp['holder'], credential.subject_did.did)

    def test_the_answer_of_the_verifier_becomes_a_message(self):
        self.user_login()
        credential = self.issued_credential()

        response = self.post_credential(credential, follow=None)

        self.assertEqual(
            [str(m) for m in response.wsgi_request._messages],
            [' Correct verification'],
        )

    def test_a_presentation_is_recorded_as_an_event(self):
        self.user_login()
        credential = self.issued_credential()

        self.post_credential(credential)

        self.assertEqual(
            Event.objects.filter(
                type=Event.Types.EV_CREDENTIAL_PRESENTED
            ).count(),
            1,
        )

    def test_a_textual_answer_is_shown_and_logged_against_the_user(self):
        self.user_login()
        credential = self.issued_credential()
        self.requests.post.return_value = peer_answers(
            verify='Ok, Correct verification', response='Validation Code 42'
        )

        response = self.post_credential(credential)

        self.assertRedirects(
            response, reverse('idhub:user_dashboard'),
            fetch_redirect_response=False,
        )
        self.assertEqual(
            Event.objects.filter(
                type=Event.Types.EV_USR_SEND_VP, user=self.user
            ).count(),
            1,
        )

    def test_a_redirection_asked_for_by_the_verifier_is_followed(self):
        self.user_login()
        credential = self.issued_credential()
        self.requests.post.return_value = peer_answers(
            verify='Ok, Correct verification',
            redirect_uri='https://verifier.example.org/thanks',
        )

        response = self.post_credential(credential)

        self.assertRedirects(
            response, 'https://verifier.example.org/thanks',
            fetch_redirect_response=False,
        )

    def test_a_rejected_presentation_is_reported_as_an_error(self):
        self.user_login()
        credential = self.issued_credential()
        self.requests.post.return_value = peer_answers(
            verify='Error, Failed verification'
        )

        response = self.post_credential(credential)

        self.assertEqual(
            [str(m) for m in response.wsgi_request._messages],
            [' Failed verification'],
        )

    def test_a_peer_that_does_not_answer_200_is_reported_as_an_error(self):
        self.user_login()
        credential = self.issued_credential()
        self.requests.post.return_value = peer_answers(status_code=500)

        response = self.post_credential(credential)

        self.assertEqual(
            [str(m) for m in response.wsgi_request._messages],
            ['Error sending credential!'],
        )
        self.assertFalse(
            Event.objects.filter(type=Event.Types.EV_CREDENTIAL_PRESENTED).exists()
        )

    def test_a_peer_that_does_not_answer_json_is_reported_as_an_error(self):
        self.user_login()
        credential = self.issued_credential()
        self.requests.post.return_value.json.side_effect = ValueError

        response = self.post_credential(credential)

        self.assertEqual(
            [str(m) for m in response.wsgi_request._messages],
            ['Error sending credential!'],
        )

    def test_the_credential_is_not_consumed_by_presenting_it(self):
        self.user_login()
        credential = self.issued_credential()

        self.post_credential(credential)

        credential.refresh_from_db()
        self.assertEqual(credential.status, VerificableCredential.Status.ISSUED)

    # Refusals

    def test_a_request_without_a_code_is_refused_by_the_form(self):
        self.user_login()
        credential = self.issued_credential()

        response = self.post_credential(credential, code=None)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "There isn't code in request",
            response.context['form'].errors['__all__'],
        )
        self.requests.post.assert_not_called()

    def test_the_credential_of_another_user_is_not_a_valid_choice(self):
        other = factories.make_user('other@example.org', 'otherpass12')
        alien = factories.make_issued_credential(other)
        self.user_login()
        self.issued_credential()

        response = self.post_credential(alien)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.requests.post.assert_not_called()

    def test_choosing_nothing_sends_nothing(self):
        self.user_login()
        self.issued_credential()

        response = self.client.post(self.url(), {})

        self.assertEqual(response.status_code, 200)
        self.requests.post.assert_not_called()


class VerifierAnswerParsingTest(IdHubTestCase):
    """``result, msg = verify.split(",")`` trusts the peer completely."""

    def setUp(self):
        super().setUp()
        self.verifier = Organization.objects.create(
            name='Verifier',
            response_uri='https://verifier.example.org/oidc4vp/',
            my_client_id='my-client-id',
            my_client_secret='my-client-secret',
        )
        patcher = patch('oidc4vp.models.requests')
        self.requests = patcher.start()
        self.addCleanup(patcher.stop)
        self.credential = factories.make_issued_credential(self.user)
        self.user_login()

    def post(self, **payload):
        self.requests.post.return_value = peer_answers(**payload)
        url = '{}?{}'.format(
            reverse('oidc4vp:authorize'),
            urlencode({
                'client_id': self.verifier.client_id,
                'presentation_definition': PRESENTATION_DEFINITION,
                'code': CODE,
            }),
        )
        return self.client.post(
            url, {CREDENTIAL_TYPE.lower(): str(self.credential.id)}
        )

    def test_a_verdict_without_a_comma_crashes_the_holder(self):
        with self.assertRaises(ValueError):
            self.post(verify='Ok')

    def test_a_missing_verdict_crashes_the_holder(self):
        with self.assertRaises(AttributeError):
            self.post(response='Validation Code 42')

    def test_a_verdict_that_is_neither_ok_nor_error_is_silently_dropped(self):
        response = self.post(verify='Maybe, we are not sure')

        self.assertEqual([str(m) for m in response.wsgi_request._messages], [])
