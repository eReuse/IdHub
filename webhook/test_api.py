"""The webhook API: ``/webhook/verify/`` and ``/webhook/sign/``.

Both are plain functions rather than views: csrf-exempt, authenticated with a
bearer token from the ``Token`` table and answering json. They share the same
four-step gate (service available, bearer header, live token, parsable body)
and then diverge.

``/webhook/sign/`` had no tests at all. It turns out its default behaviour --
``save`` omitted, which is documented as ``True`` -- always answers 400 and
stores nothing, because ``issue(save=True)`` returns ``None``. Only an explicit
``"save": false`` ever produces a credential.
"""
import json

from uuid import uuid4

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.urls import reverse

from idhub.mixins import Http403
from idhub.models import VerificableCredential
from idhub_auth.models import User
from test_support import factories
from test_support.base import IdHubTestCase
from webhook.models import Token


SCHEMA_FILE = 'device-snapshot-v1.json'

# What workbench-script posts: the snapshot of one machine. ``operator_id``
# and the three command outputs are the keys webhook_issue rewrites.
SNAPSHOT = {
    'uuid': '0f2b2d57-6a14-4b94-8f5f-2b64f7a7d1c2',
    'type': 'hardwareList',
    'software': 'workbench-script',
    'timestamp': '2024-06-11T14:41:12Z',
    'operator_id': 'abcdefghij1234567890',
    'data': {'dmidecode': 'dmi output', 'inxi': 'inxi output',
             'smartctl': 'smartctl output'},
}

BOTH = ('webhook:verify', 'webhook:sign')


class WebhookTestCase(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.token = Token.objects.create(token=uuid4(), label='Workbench')

    def post(self, name, payload=None, body=None, token=None, headers=None):
        if headers is None:
            headers = {'Authorization': 'Bearer {}'.format(
                self.token.token if token is None else token
            )}
        return self.client.post(
            reverse(name),
            data=json.dumps(payload) if body is None else body,
            content_type='application/json',
            headers=headers,
        )


class TokenGateTest(WebhookTestCase):
    """The four checks both endpoints run before looking at the payload."""

    def test_a_get_is_refused_with_four_hundred_instead_of_four_oh_five(self):
        for name in BOTH:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json(), {'error': 'Invalid request method'}
                )

    def test_without_the_encryption_key_the_service_declares_itself_down(self):
        cache.set('KEY_DIDS', None)
        for name in BOTH:
            with self.subTest(url=name):
                response = self.post(name, {})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json(), {'error': 'Temporary out of service'}
                )

    def test_an_admin_who_has_not_accepted_the_terms_takes_it_down_too(self):
        self.admin_user.accept_gdpr = False
        self.admin_user.save()
        for name in BOTH:
            with self.subTest(url=name):
                self.assertEqual(
                    self.post(name, {}).json(),
                    {'error': 'Temporary out of service'},
                )

    def test_an_instance_with_no_admin_at_all_crashes(self):
        # The gate reads user.accept_gdpr without checking that the query
        # found anything, so the endpoint answers 500 rather than reporting
        # the same "out of service" as every other unavailable state.
        User.objects.filter(is_admin=True).delete()
        for name in BOTH:
            with self.subTest(url=name):
                with self.assertRaises(AttributeError):
                    self.post(name, {})

    def test_a_missing_or_unprefixed_authorization_header_is_unauthorized(self):
        for headers in ({}, {'Authorization': 'Basic xyz'},
                        {'Authorization': str(uuid4())}):
            for name in BOTH:
                with self.subTest(url=name, headers=headers):
                    response = self.post(name, {}, headers=headers)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(
                        response.json(), {'error': 'Invalid or missing token'}
                    )

    def test_an_unknown_token_is_unauthorized(self):
        for name in BOTH:
            with self.subTest(url=name):
                self.assertEqual(
                    self.post(name, {}, token=uuid4()).status_code, 401
                )

    def test_a_deactivated_token_is_unauthorized(self):
        self.token.active = False
        self.token.save()
        for name in BOTH:
            with self.subTest(url=name):
                self.assertEqual(self.post(name, {}).status_code, 401)

    def test_a_token_that_is_not_a_uuid_crashes_instead_of_being_rejected(self):
        # Token.token is a UUIDField, so the lookup that is meant to reject a
        # forged token raises ValidationError on the way in: anything that is
        # not uuid-shaped is a 500 rather than a 401.
        for name in BOTH:
            with self.subTest(url=name):
                with self.assertRaises(ValidationError):
                    self.post(name, {}, token='not-a-uuid')

    def test_the_quotes_a_shell_leaves_around_the_token_are_stripped(self):
        # Reaching the body check is the proof that the token was accepted.
        for quoted in ("'{}'", '"{}"'):
            for name in BOTH:
                with self.subTest(url=name, quoted=quoted):
                    response = self.post(
                        name, body='{not json',
                        token=quoted.format(self.token.token),
                    )
                    self.assertEqual(response.json(), {'error': 'Invalid JSON'})

    def test_a_body_that_is_not_json_is_rejected(self):
        for name in BOTH:
            with self.subTest(url=name):
                response = self.post(name, body='{not json')
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {'error': 'Invalid JSON'})


class VerifyTest(WebhookTestCase):
    def test_a_payload_that_is_not_a_credential_is_reported_as_a_failure(self):
        response = self.post(
            'webhook:verify', {'type': 'credential', 'data': {'a': 1}}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {'status': 'Could not extract JWS or message from proof'},
        )

    def test_a_body_with_no_data_at_all_crashes(self):
        # There is no check that `data` is present: a missing key becomes the
        # json literal null, and verify_vp_signature reads a proof off it.
        for payload in ({}, {'type': 'vp'}, {'type': 'vp', 'data': None}):
            with self.subTest(payload=payload):
                with self.assertRaises(AttributeError):
                    self.post('webhook:verify', payload)

    def test_a_presentation_that_is_not_one_is_reported_not_raised(self):
        response = self.post('webhook:verify', {'data': {'a': 1}})

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.json()['status'], 'success')

    def test_a_credential_with_a_broken_signature_is_reported_in_the_status(self):
        # The only path that answers with an error message instead of raising:
        # a well-formed credential whose proof does not check out.
        credential = json.loads(self.signed_credential())
        credential['credentialSubject']['uuid'] = 'tampered'

        response = self.post(
            'webhook:verify', {'type': 'credential', 'data': credential}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.json()['status'], 'success')

    def test_a_credential_this_instance_signed_verifies(self):
        response = self.post('webhook:verify', {
            'type': 'credential', 'data': json.loads(self.signed_credential())
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'success'})

    def test_the_type_makes_no_difference_for_a_credential(self):
        # Only the literal "credential" picks verify_signature; everything
        # else falls through to verify_vp_signature, which happens to accept
        # a bare credential as well. The field is decoration.
        credential = json.loads(self.signed_credential())
        for typ in (None, 'presentation', 'nonsense'):
            with self.subTest(type=typ):
                response = self.post(
                    'webhook:verify', {'type': typ, 'data': credential}
                )
                self.assertEqual(response.json(), {'status': 'success'})

    def signed_credential(self):
        schema = factories.make_schema(SCHEMA_FILE)
        did = factories.make_did(label='Issuer')
        credential = factories.make_credential(
            self.user, schema, did, csv_data=dict(SNAPSHOT)
        )
        return credential.issue(did, domain='https://testserver', save=False)


class IssueTest(WebhookTestCase):
    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema(SCHEMA_FILE)
        self.did = factories.make_did(label='Issuer')
        # create_user leaves the per-user key unset and the issuer is the
        # admin, whose key encrypt_data() needs.
        self.admin_user.set_encrypted_sensitive_data()
        self.admin_user.save()

    def sign(self, **overrides):
        payload = {'type': self.schema.type, 'data': dict(SNAPSHOT)}
        payload.update(overrides)
        return self.post('webhook:sign', payload)

    def test_the_documented_default_always_fails_and_stores_nothing(self):
        # save defaults to True, issue() returns None when it saves, and the
        # view reads that None as a failure. The whole happy path of the
        # endpoint as a client would call it is unreachable, and the
        # credential it built is dropped because nobody calls cred.save().
        response = self.sign()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Invalid credential'})
        self.assertFalse(VerificableCredential.objects.exists())

    def test_asking_not_to_save_returns_the_signed_credential(self):
        response = self.sign(save=False)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertIn('proof', json.loads(response.json()['data']))

    def test_nothing_is_ever_written_to_the_database(self):
        self.sign(save=False)

        self.assertFalse(VerificableCredential.objects.exists())

    def test_the_snapshot_becomes_the_credential_subject(self):
        signed = json.loads(self.sign(save=False).json()['data'])
        subject = signed['credentialSubject']

        self.assertEqual(subject['uuid'], SNAPSHOT['uuid'])
        self.assertEqual(subject['type'], 'hardwareList')
        self.assertEqual(subject['software'], 'workbench-script')

    def test_the_underscored_operator_id_is_renamed_for_the_schema(self):
        signed = json.loads(self.sign(save=False).json()['data'])

        self.assertEqual(
            signed['credentialSubject']['operatorId'],
            SNAPSHOT['operator_id'],
        )

    def test_a_snapshot_without_an_operator_can_never_be_issued(self):
        # The fallback for a missing operator_id is "--", and the schema asks
        # operatorId for at least ten characters, so the placeholder is the
        # one value guaranteed to fail validation.
        snapshot = dict(SNAPSHOT)
        del snapshot['operator_id']

        with self.assertRaises(TypeError):
            self.sign(data=snapshot, save=False)

    def test_the_three_command_outputs_become_the_evidence(self):
        signed = json.loads(self.sign(save=False).json()['data'])

        self.assertEqual(
            [(item['operation'], item['output']) for item in signed['evidence']],
            [('dmidecode', 'dmi output'), ('smartctl', 'smartctl output'),
             ('inxi', 'inxi output')],
        )
        for item in signed['evidence']:
            self.assertEqual(item['timestamp'], SNAPSHOT['timestamp'])

    def test_a_snapshot_with_no_command_output_still_gets_three_evidences(self):
        snapshot = dict(SNAPSHOT)
        del snapshot['data']
        signed = json.loads(self.sign(data=snapshot, save=False).json()['data'])

        self.assertEqual(
            [item['output'] for item in signed['evidence']], ['""', '""', '""']
        )

    def test_the_credential_is_issued_to_the_issuer_itself(self):
        # webhook_issue passes the organisation did as both issuer and
        # subject, so the signed credential has no holder.
        signed = json.loads(self.sign(save=False).json()['data'])

        self.assertEqual(signed['issuer']['id'], self.did.did)
        self.assertEqual(signed['credentialSubject']['id'], self.did.did)

    def test_the_url_of_an_unsaved_credential_is_always_credentials_zero(self):
        # get_context falls back to 0 when the row has no primary key, and
        # since nothing is ever saved every credential claims the same id.
        signed = json.loads(self.sign(save=False).json()['data'])

        self.assertTrue(signed['id'].endswith('/credentials/0'))

    def test_an_unknown_type_is_an_invalid_credential(self):
        response = self.sign(type='NoSuchSchema', save=False)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Invalid credential'})

    def test_without_an_organisation_did_there_is_nothing_to_sign_with(self):
        self.did.delete()
        response = self.sign(save=False)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Invalid DID'})

    def test_a_did_that_belongs_to_a_user_is_not_used(self):
        # The lookup filters on user__isnull, so a wallet did cannot be
        # borrowed to sign an incoming snapshot.
        self.did.delete()
        factories.make_did(label='Wallet', user=self.user)
        self.assertEqual(self.sign(save=False).json(), {'error': 'Invalid DID'})

    def test_a_snapshot_the_schema_rejects_crashes(self):
        # issue() means to raise Exception("The credential is not valid with
        # this schema"), but the line above rebinds the gettext alias `_` to
        # the error string, so the raise calls a str. The endpoint answers
        # 500 and the real reason never reaches the log.
        with self.assertRaises(TypeError):
            self.sign(data={'type': 'hardwareList'}, save=False)

    def test_a_missing_type_is_rejected_as_invalid_json(self):
        for payload in ({}, {'data': SNAPSHOT}):
            with self.subTest(payload=sorted(payload)):
                response = self.post('webhook:sign', payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), {'error': 'Invalid JSON'})

    def test_a_missing_data_is_not_caught_by_that_same_check(self):
        # The guard tests `not vc` after vc has already been through
        # json.dumps, and json.dumps(None) is the string "null", which is
        # truthy. The payload sails past it and crashes further in.
        for payload in ({'type': self.schema.type},
                        {'type': self.schema.type, 'data': None}):
            with self.subTest(payload=payload):
                with self.assertRaises(TypeError):
                    self.post('webhook:sign', payload)


class TokenAdminTest(WebhookTestCase):
    """The token pages, and who can reach them."""

    def url(self, name, *args):
        return reverse('webhook:{}'.format(name), args=args)

    def test_an_admin_toggles_a_token_off_and_on_again(self):
        self.admin_login()
        for expected in (False, True):
            with self.subTest(active=expected):
                self.client.get(self.url('status_token', self.token.id))
                self.token.refresh_from_db()
                self.assertEqual(self.token.active, expected)

    def test_toggling_redirects_back_to_the_token_list(self):
        self.admin_login()
        response = self.client.get(self.url('status_token', self.token.id))

        self.assertEqual(response['Location'], self.url('tokens'))

    def test_a_new_token_is_active_and_has_a_uuid_of_its_own(self):
        self.admin_login()
        self.client.post(self.url('new_token'), data={'label': 'Second'})
        created = Token.objects.get(label='Second')

        self.assertTrue(created.active)
        self.assertNotEqual(created.token, self.token.token)

    def test_the_list_page_bounces_a_plain_user(self):
        self.user_login()
        for name in ('tokens', 'new_token'):
            with self.subTest(url=name):
                response = self.client.get(self.url(name))
                self.assertEqual(
                    response['Location'], reverse('idhub:user_dashboard')
                )

    def test_a_plain_user_can_delete_and_disable_any_token(self):
        # The same discarded check_valid_user() as the seventeen admin views
        # in test_permissions.py: two more entries, in another app.
        self.user_login()
        self.client.get(self.url('status_token', self.token.id))
        self.token.refresh_from_db()
        self.assertFalse(self.token.active)

        self.client.get(self.url('delete_token', self.token.id))
        self.assertFalse(Token.objects.exists())

    def test_an_anonymous_visitor_is_sent_to_the_login_page(self):
        for name in ('tokens', 'new_token', 'status_token', 'delete_token'):
            with self.subTest(url=name):
                args = [] if name in ('tokens', 'new_token') else [self.token.id]
                response = self.client.get(self.url(name, *args))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/login/?next='))


class Http403Test(SimpleTestCase):
    """The exception class, which is only ever raised with no arguments."""

    def test_raised_bare_it_carries_no_message_at_all(self):
        # default_detail is never copied onto the instance, so the 403 page
        # shows Django's generic text instead of the sentence above it.
        error = Http403()

        self.assertFalse(hasattr(error, 'detail'))
        self.assertEqual(str(error), '')

    def test_a_detail_passed_in_is_kept(self):
        error = Http403('Not your credential')

        self.assertEqual(error.detail, 'Not your credential')
        self.assertEqual(str(error), 'Not your credential')

    def test_an_empty_detail_crashes_on_a_misspelt_class_attribute(self):
        # __init__ falls back to self.default_details; the attribute is
        # called default_detail.
        with self.assertRaises(AttributeError):
            Http403('')

    def test_a_code_is_kept_and_an_empty_one_falls_back(self):
        self.assertEqual(Http403(code='expired').code, 'expired')
        self.assertEqual(Http403(code='').code, 'forbidden')

    def test_the_code_never_reaches_the_message(self):
        self.assertEqual(str(Http403(code='expired')), '')
