"""Tests for the v1 API of idhub/api/api.py.

A django-ninja API mounted at /api/v1/ by trustchain_idhub/urls.py. It is the
machine-to-machine face of the UNTP work: six endpoints that create product
DIDs, keep their service endpoint in step and issue the three UNTP credential
types, all behind a bearer token stored in webhook.Token.

The endpoints are tested through the URL, as a client sees them, because the
contract that matters here is the HTTP one: which status code comes back and
what the body says. The two services behind them (CredentialIssuanceService
and DIDService) have their own tests in test_services.py, so they are patched
by name whenever the subject is the endpoint and not the issuance: an
unforeseen call then fails loudly instead of signing or going out to the
network.
"""
import json

from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from ninja.errors import ConfigError

from idhub.api.api import DatabaseTokenAuth, _find_issuer_did
from idhub.forms import VerificationForm
from idhub.models import DID, Schemas, VerificableCredential
from idhub.services import VerificationService
from test_support import factories
from test_support.base import IdHubTestCase
from webhook.models import Token


ISSUE_PATHS = {
    'dpp': '/api/v1/issue-dpp/',
    'facility': '/api/v1/issue-facility/',
    'traceability': '/api/v1/issue-traceability/',
}

SCHEMAS_PATH = '/api/v1/schemas/untp/active/'
CREATE_DID_PATH = '/api/v1/object-did/create/'
UPDATE_DID_PATH = '/api/v1/object-did/update/'


def untp_schema(file_name, types, description='A schema'):
    """A schema row whose declared types make Schemas.is_untp answer.

    is_untp reads properties.type.default, so that is the only part of the
    document that has to be real. No UNTP schema ships in schemas/, which is
    why these are built by hand rather than with factories.make_schema.
    """
    data = {
        'title': file_name,
        'name': 'Schema',
        'description': description,
        'properties': {'type': {'default': types}},
    }
    return Schemas.objects.create(
        file_schema=file_name,
        data=json.dumps(data),
        type=types[-1] if types else '',
        _name=json.dumps('Schema'),
        _description=json.dumps(description),
        validation_url='https://testserver/schemas/{}'.format(file_name),
    )


class ApiTestCase(IdHubTestCase):
    """An admin-owned active token, which is what the auth class demands."""

    def setUp(self):
        super().setUp()
        self.token = Token.objects.create(label='api', owner=self.admin_user)

    def bearer(self, token=None):
        value = self.token.token if token is None else token
        return {'HTTP_AUTHORIZATION': 'Bearer {}'.format(value)}

    def post(self, path, payload, token=None, **kwargs):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type='application/json',
            **{**self.bearer(token), **kwargs},
        )

    def patched(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock


class DatabaseTokenAuthTest(ApiTestCase):
    """DatabaseTokenAuth: an active token owned by an active admin, or 401."""

    def get_schemas(self, token=None, **kwargs):
        return self.client.get(SCHEMAS_PATH, **{**self.bearer(token), **kwargs})

    def test_a_request_with_no_authorization_header_is_refused(self):
        self.assertEqual(self.client.get(SCHEMAS_PATH).status_code, 401)

    def test_a_valid_token_is_accepted(self):
        self.assertEqual(self.get_schemas().status_code, 200)

    def test_a_token_that_does_not_exist_is_refused(self):
        self.assertEqual(
            self.get_schemas('0cc7bb5a-1d7e-4f6e-9a0f-2b0d5e4a1c33').status_code,
            401,
        )

    def test_a_token_that_is_not_a_uuid_is_refused_and_not_a_crash(self):
        """The contrast with the webhook, where the same input is a 500.

        Token.token is a UUIDField, so filtering by a string that is not
        uuid-shaped raises ValidationError. Here the blanket except in
        authenticate() turns it into a plain 401; webhook/views.py has no
        such guard, which is B26.
        """
        self.assertEqual(self.get_schemas('not-a-uuid').status_code, 401)

    def test_an_inactive_token_is_refused(self):
        self.token.active = False
        self.token.save()

        self.assertEqual(self.get_schemas().status_code, 401)

    def test_a_token_with_no_owner_is_refused(self):
        self.token.owner = None
        self.token.save()

        self.assertEqual(self.get_schemas().status_code, 401)

    def test_a_token_owned_by_a_plain_user_is_refused(self):
        """is_admin is the only role the API accepts."""
        self.token.owner = self.user
        self.token.save()

        self.assertEqual(self.get_schemas().status_code, 401)

    def test_a_token_owned_by_a_deactivated_admin_is_refused(self):
        self.admin_user.is_active = False
        self.admin_user.save()

        self.assertEqual(self.get_schemas().status_code, 401)

    def test_the_scheme_has_to_be_bearer(self):
        response = self.client.get(
            SCHEMAS_PATH,
            HTTP_AUTHORIZATION='Token {}'.format(self.token.token),
        )

        self.assertEqual(response.status_code, 401)


class FindIssuerDidTest(ApiTestCase):
    """_find_issuer_did: the issuer has to be an organization DID.

    Called straight rather than through a request, because the two branches
    that matter cannot both be reached over HTTP: the empty-did one is
    unreachable (the payload demands min_length=1) and the allowed_dids one
    is never taken at all. See AllowedDidsGuardTest.
    """

    class FakeRequest:
        pass

    def request_with(self, **attrs):
        request = self.FakeRequest()
        for name, value in attrs.items():
            setattr(request, name, value)
        return request

    def test_an_organization_did_is_returned(self):
        did = factories.make_did(label='Issuer')

        self.assertEqual(_find_issuer_did(did.did, self.request_with()), did)

    def test_an_empty_did_is_a_value_error(self):
        """A 400 through the exception handler, but unreachable over HTTP."""
        for requested in ('', None):
            with self.subTest(requested=requested):
                with self.assertRaises(ValueError):
                    _find_issuer_did(requested, self.request_with())

    def test_a_did_that_does_not_exist_is_permission_denied(self):
        """Not found and not allowed answer the same way: both are a 403."""
        with self.assertRaises(PermissionDenied):
            _find_issuer_did('did:web:testserver:nope', self.request_with())

    def test_a_did_that_belongs_to_a_user_is_not_an_issuer(self):
        did = factories.make_did(label='Personal', user=self.admin_user)

        with self.assertRaises(PermissionDenied):
            _find_issuer_did(did.did, self.request_with())

    def test_a_product_did_is_not_an_issuer(self):
        did = DID.objects.create(label='Product', type=DID.Types.WEB.value,
                                 did='did:web:testserver:product',
                                 is_product=True)

        with self.assertRaises(PermissionDenied):
            _find_issuer_did(did.did, self.request_with())


class AllowedDidsGuardTest(ApiTestCase):
    """Token.allowed_dids restricts nothing: the guard is never reached.

    webhook.Token grew an allowed_dids relation so a token could be tied to
    the issuer DIDs it may use, and _find_issuer_did reads it. But it looks
    the restriction up under request.auth_token, while DatabaseTokenAuth
    stores the row as request.token: the getattr always answers None and the
    branch is skipped. Dead code, in the same family as B47 and B50.

    This is not a privilege escalation -the issuer still has to be an
    organization DID and the token still has to belong to an admin- but the
    per-token restriction the field promises does not happen.
    """

    def setUp(self):
        super().setUp()
        self.issuer = factories.make_did(label='Issuer')
        self.other = factories.make_did(label='Other issuer')
        self.issue = self.patched(
            'idhub.api.api.CredentialIssuanceService.issue_untp_credential',
            return_value=(201, {'credential': {'id': 'urn:uuid:1'}}),
        )

    def issue_dpp(self, did):
        return self.post(ISSUE_PATHS['dpp'], {
            'schema_name': 'dpp.json',
            'issuer_did': did.did,
            'credentialSubject': {'id': 'did:web:testserver:product'},
        })

    def test_the_authenticator_stores_the_token_under_another_name(self):
        """The cause, in two assertions: token is set, auth_token is not."""
        class FakeRequest:
            pass

        request = FakeRequest()
        DatabaseTokenAuth().authenticate(request, str(self.token.token))

        self.assertEqual(request.token, self.token)
        self.assertFalse(hasattr(request, 'auth_token'))

    def test_a_token_allowed_nothing_still_issues_with_any_issuer(self):
        self.assertEqual(self.token.allowed_dids.count(), 0)

        self.assertEqual(self.issue_dpp(self.issuer).status_code, 201)

    def test_a_token_allowed_one_did_still_issues_with_another(self):
        self.token.allowed_dids.add(self.other)

        self.assertEqual(self.issue_dpp(self.issuer).status_code, 201)

    def test_the_guard_does_fire_when_the_attribute_is_the_one_it_reads(self):
        """The logic itself works; only the attribute name is wrong.

        Feeding _find_issuer_did a request carrying auth_token -what the
        function looks for- takes the branch and refuses. Whoever fixes the
        authenticator can expect this to be the behaviour over HTTP.
        """
        class FakeRequest:
            pass

        request = FakeRequest()
        request.auth_token = self.token
        self.token.allowed_dids.add(self.other)

        with self.assertRaises(PermissionDenied):
            _find_issuer_did(self.issuer.did, request)

        self.assertEqual(_find_issuer_did(self.other.did, request), self.other)


class CreateObjectDidTest(ApiTestCase):
    """POST object-did/create/: the product DID a device is given."""

    def create(self, **payload):
        return self.post(CREATE_DID_PATH, payload)

    def test_a_new_did_is_created_and_answered_with_201(self):
        response = self.create(suffix_did_id='device-1')

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['did'], 'did:web:testserver:device-1')
        self.assertEqual(body['did_document']['id'], body['did'])

        did = DID.objects.get(did=body['did'])
        self.assertTrue(did.is_product)
        self.assertEqual(did.user, self.admin_user)

    def test_asking_twice_for_the_same_suffix_answers_200_and_does_not_duplicate(self):
        first = self.create(suffix_did_id='device-1')
        second = self.create(suffix_did_id='device-1')

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()['did'], second.json()['did'])
        self.assertEqual(DID.objects.filter(is_product=True).count(), 1)

    def services_of(self, response, type):
        return [
            s for s in response.json()['did_document'].get('service', [])
            if s['type'] == type
        ]

    def test_the_service_endpoint_is_written_into_the_did_document(self):
        response = self.create(
            suffix_did_id='device-1',
            service_endpoint='https://example.org/passport',
        )

        self.assertEqual(response.status_code, 201)
        passport = self.services_of(response, 'ProductPassport')
        self.assertEqual(
            [s['serviceEndpoint'] for s in passport], ['https://example.org/passport']
        )
        self.assertEqual(passport[0]['id'], '{}#product'.format(response.json()['did']))

    def test_with_no_endpoint_there_is_no_passport_service(self):
        """The service list is never empty even so: gen_did_document always
        writes a RevocationBitmap2022 entry, so the branch of
        sync_endpoint_to_document that deletes an empty service list is
        unreachable for a did:web built this way."""
        response = self.create(suffix_did_id='device-1')

        self.assertEqual(self.services_of(response, 'ProductPassport'), [])
        self.assertEqual(
            [s['type'] for s in response.json()['did_document']['service']],
            ['RevocationBitmap2022'],
        )
        self.assertIsNone(response.json()['service_endpoint'])

    def test_the_label_defaults_to_the_suffix_behind_a_device_prefix(self):
        """A suffix that already reads like a device name is prefixed again:
        'device-1' becomes the label 'device-device-1'."""
        self.create(suffix_did_id='laptop-42')
        self.assertEqual(DID.objects.get(is_product=True).label, 'device-laptop-42')

        DID.objects.all().delete()

        self.create(suffix_did_id='device-1')
        self.assertEqual(DID.objects.get(is_product=True).label, 'device-device-1')

    def test_a_label_that_is_given_is_kept(self):
        self.create(suffix_did_id='device-1', label='Laptop 42')

        self.assertEqual(DID.objects.get(is_product=True).label, 'Laptop 42')

    def test_a_missing_suffix_is_a_validation_error(self):
        self.assertEqual(self.post(CREATE_DID_PATH, {}).status_code, 422)

    def test_an_endpoint_that_is_not_a_url_is_a_validation_error(self):
        response = self.create(suffix_did_id='device-1', service_endpoint='nope')

        self.assertEqual(response.status_code, 422)

    def test_a_failure_in_the_service_is_a_500_with_no_detail(self):
        self.patched(
            'idhub.api.api.DIDService.get_or_create_product_did',
            side_effect=Exception('boom'),
        )

        response = self.create(suffix_did_id='device-1')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {'error': 'Internal server error during DID creation.',
             'details': None, 'path': None},
        )

    def test_the_endpoint_needs_a_token(self):
        response = self.client.post(
            CREATE_DID_PATH,
            data=json.dumps({'suffix_did_id': 'device-1'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(DID.objects.filter(is_product=True).exists())


class UpdateServiceEndpointTest(ApiTestCase):
    """POST object-did/update/: moving the passport of an existing DID."""

    def setUp(self):
        super().setUp()
        self.did = DID.objects.create(
            label='Product',
            type=DID.Types.WEB.value,
            did='did:web:testserver:device-1',
            is_product=True,
            user=self.admin_user,
            didweb_document=json.dumps({
                '@context': ['https://www.w3.org/ns/did/v1'],
                'id': 'did:web:testserver:device-1',
            }),
        )

    def update(self, did=None, endpoint='https://example.org/new'):
        return self.post(UPDATE_DID_PATH, {
            'did': self.did.did if did is None else did,
            'service_endpoint': endpoint,
        })

    def test_the_endpoint_is_stored_and_answered(self):
        response = self.update()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'success': True,
            'did': self.did.did,
            'service_endpoint': 'https://example.org/new',
        })

        self.did.refresh_from_db()
        self.assertEqual(self.did.service_endpoint, 'https://example.org/new')

    def test_the_did_document_is_kept_in_step(self):
        self.update()
        self.did.refresh_from_db()

        service = json.loads(self.did.didweb_document)['service']
        self.assertEqual(
            [s['serviceEndpoint'] for s in service], ['https://example.org/new']
        )

    def test_updating_twice_does_not_leave_two_passport_services(self):
        self.update(endpoint='https://example.org/one')
        self.update(endpoint='https://example.org/two')
        self.did.refresh_from_db()

        service = json.loads(self.did.didweb_document)['service']
        self.assertEqual(
            [s['serviceEndpoint'] for s in service], ['https://example.org/two']
        )

    def test_a_did_that_does_not_exist_is_a_404(self):
        response = self.update(did='did:web:testserver:nope')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {'error': 'DID not found or you do not have permission to modify it.',
             'details': None, 'path': None},
        )

    def test_a_did_that_belongs_to_somebody_else_is_a_404(self):
        self.did.user = self.user
        self.did.save()

        self.assertEqual(self.update().status_code, 404)

    def test_a_did_that_is_not_a_product_is_a_404(self):
        self.did.is_product = False
        self.did.save()

        self.assertEqual(self.update().status_code, 404)

    def test_a_missing_endpoint_is_a_validation_error(self):
        response = self.post(UPDATE_DID_PATH, {'did': self.did.did})

        self.assertEqual(response.status_code, 422)

    def test_the_error_handler_of_this_endpoint_cannot_answer_at_all(self):
        """Its except returns a 500 the decorator never declared.

        response= lists 200, 403 and 404 only, so when the body is built
        django-ninja refuses it with ConfigError and the carefully written
        'Internal server error updating the DID.' never reaches the client:
        what comes out is an unhandled exception. The sibling endpoint
        object-did/create/ does declare 500 and does answer it, so this is
        an oversight in one decorator and not a decision.
        """
        self.patched(
            'idhub.api.api.DIDService.sync_endpoint_to_document',
            side_effect=Exception('boom'),
        )

        with self.assertRaises(ConfigError) as caught:
            self.update()

        self.assertIn('Schema for status 500 is not set', str(caught.exception))

        self.did.refresh_from_db()
        self.assertEqual(self.did.service_endpoint, '')

    def test_the_endpoint_needs_a_token(self):
        response = self.client.post(
            UPDATE_DID_PATH,
            data=json.dumps({
                'did': self.did.did,
                'service_endpoint': 'https://example.org/new',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.did.refresh_from_db()
        self.assertEqual(self.did.service_endpoint, '')


class IssueEndpointTestCase(ApiTestCase):
    """Shared ground for the three issue endpoints.

    CredentialIssuanceService is patched: what is under test is what the
    endpoint hands it and what it does with the answer, not the signing.
    """

    def setUp(self):
        super().setUp()
        self.issuer = factories.make_did(label='Issuer')
        self.issue = self.patched(
            'idhub.api.api.CredentialIssuanceService.issue_untp_credential',
            return_value=(201, {'credential': {'id': 'urn:uuid:1'}}),
        )

    def product_did(self, did='did:web:testserver:device-1'):
        return DID.objects.create(
            label='Product', type=DID.Types.WEB.value, did=did, is_product=True
        )

    def call_kwargs(self):
        self.assertEqual(self.issue.call_count, 1)
        return self.issue.call_args.kwargs


class IssueDppTest(IssueEndpointTestCase):
    """POST issue-dpp/: the product passport."""

    def issue_dpp(self, subject=None, issuer=None, schema='dpp.json'):
        return self.post(ISSUE_PATHS['dpp'], {
            'schema_name': schema,
            'issuer_did': self.issuer.did if issuer is None else issuer,
            'credentialSubject': {
                'id': 'did:web:testserver:device-1'
            } if subject is None else subject,
        })

    def test_the_signed_credential_is_answered_with_201(self):
        response = self.issue_dpp()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'credential': {'id': 'urn:uuid:1'}})

    def test_the_service_is_asked_for_a_digital_product_passport(self):
        self.issue_dpp()

        kwargs = self.call_kwargs()
        self.assertEqual(
            kwargs['credential_type'],
            ['VerifiableCredential', 'DigitalProductPassport'],
        )
        self.assertEqual(kwargs['schema_name'], 'dpp.json')
        self.assertEqual(kwargs['issuer_did_obj'], self.issuer)
        self.assertEqual(kwargs['user'], self.admin_user)

    def test_the_subject_id_is_resolved_to_the_product_did(self):
        product = self.product_did()

        self.issue_dpp()

        self.assertEqual(self.call_kwargs()['subject_did'], product)

    def test_a_subject_with_no_matching_did_is_issued_with_none(self):
        """No product DID on file is not an error: the subject goes unlinked."""
        self.issue_dpp()

        self.assertIsNone(self.call_kwargs()['subject_did'])

    def test_a_subject_with_no_id_is_issued_with_none(self):
        self.issue_dpp(subject={'serialNumber': '42'})

        self.assertIsNone(self.call_kwargs()['subject_did'])

    def test_the_subject_reaches_the_service_untouched(self):
        self.issue_dpp(subject={'id': 'did:web:testserver:device-1', 'weight': 0})

        self.assertEqual(
            self.call_kwargs()['subject_data'],
            {'id': 'did:web:testserver:device-1', 'weight': 0},
        )

    def test_an_issuer_that_is_not_ours_is_a_403(self):
        response = self.issue_dpp(issuer='did:web:elsewhere.example:issuer')

        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.json())
        self.issue.assert_not_called()

    def test_a_schema_the_service_rejects_is_passed_through(self):
        self.issue.return_value = (422, {'error': "Schema 'x' does not exist."})

        response = self.issue_dpp()

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error'], "Schema 'x' does not exist.")

    def test_a_failed_validation_is_passed_through_with_its_detail(self):
        self.issue.return_value = (
            400,
            {'error': 'Schema validation failed prior to signing.',
             'details': 'weight is required'},
        )

        response = self.issue_dpp()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['details'], 'weight is required')

    def test_a_value_error_from_the_service_is_turned_into_a_400(self):
        """The api-wide ValueError handler. Nothing in the endpoints reaches
        it on its own -the only raise of ValueError, in _find_issuer_did, is
        unreachable- so it only fires for one coming out of the issuance."""
        self.issue.side_effect = ValueError('subject is not a product')

        response = self.issue_dpp()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'subject is not a product'})

    def test_a_missing_schema_name_is_a_validation_error(self):
        response = self.post(ISSUE_PATHS['dpp'], {
            'issuer_did': self.issuer.did, 'credentialSubject': {},
        })

        self.assertEqual(response.status_code, 422)
        self.issue.assert_not_called()

    def test_an_empty_issuer_is_refused_before_the_view_runs(self):
        """min_length=1 on the payload makes the ValueError branch of
        _find_issuer_did unreachable: this is a 422, never the 400 the
        exception handler would produce."""
        response = self.post(ISSUE_PATHS['dpp'], {
            'schema_name': 'dpp.json',
            'issuer_did': '',
            'credentialSubject': {},
        })

        self.assertEqual(response.status_code, 422)

    def test_the_endpoint_needs_a_token(self):
        response = self.client.post(
            ISSUE_PATHS['dpp'],
            data=json.dumps({
                'schema_name': 'dpp.json',
                'issuer_did': self.issuer.did,
                'credentialSubject': {},
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)
        self.issue.assert_not_called()


class IssueFacilityTest(IssueEndpointTestCase):
    """POST issue-facility/: the facility record, which is self-signed."""

    def issue_facility(self, issuer=None):
        return self.post(ISSUE_PATHS['facility'], {
            'schema_name': 'dfr.json',
            'issuer_did': self.issuer.did if issuer is None else issuer,
            'credentialSubject': {'name': 'A workshop'},
        })

    def test_the_signed_credential_is_answered_with_201(self):
        self.assertEqual(self.issue_facility().status_code, 201)

    def test_the_service_is_asked_for_a_digital_facility_record(self):
        self.issue_facility()

        self.assertEqual(
            self.call_kwargs()['credential_type'],
            ['VerifiableCredential', 'DigitalFacilityRecord'],
        )

    def test_the_issuer_is_also_the_subject(self):
        """Self-signing, flagged with a TODO in the code: the facility
        record is issued about the issuer itself."""
        self.issue_facility()

        kwargs = self.call_kwargs()
        self.assertEqual(kwargs['subject_did'], self.issuer)
        self.assertEqual(kwargs['subject_did'], kwargs['issuer_did_obj'])

    def test_an_issuer_that_is_not_ours_is_a_403(self):
        response = self.issue_facility(issuer='did:web:elsewhere.example:issuer')

        self.assertEqual(response.status_code, 403)
        self.issue.assert_not_called()

    def test_the_endpoint_needs_a_token(self):
        response = self.client.post(
            ISSUE_PATHS['facility'],
            data=json.dumps({
                'schema_name': 'dfr.json',
                'issuer_did': self.issuer.did,
                'credentialSubject': {},
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)


class IssueTraceabilityTest(IssueEndpointTestCase):
    """POST issue-traceability/: a batch of events, not a single subject."""

    def issue_events(self, events=None, issuer=None):
        return self.post(ISSUE_PATHS['traceability'], {
            'schema_name': 'dte.json',
            'issuer_did': self.issuer.did if issuer is None else issuer,
            'credentialSubject': [
                {'id': 'did:web:testserver:device-1', 'eventType': 'repair'}
            ] if events is None else events,
        })

    def test_the_signed_credential_is_answered_with_201(self):
        self.assertEqual(self.issue_events().status_code, 201)

    def test_the_service_is_asked_for_a_digital_traceability_event(self):
        self.issue_events()

        self.assertEqual(
            self.call_kwargs()['credential_type'],
            ['VerifiableCredential', 'DigitalTraceabilityEvent'],
        )

    def test_the_whole_list_of_events_is_the_subject(self):
        events = [
            {'id': 'did:web:testserver:device-1', 'eventType': 'repair'},
            {'id': 'did:web:testserver:device-1', 'eventType': 'resale'},
        ]

        self.issue_events(events)

        self.assertEqual(self.call_kwargs()['subject_data'], events)

    def test_only_the_first_event_decides_the_subject_did(self):
        """A batch whose events are about different products links only the
        first one: the rest are signed into a credential that does not name
        them as its subject."""
        product = self.product_did()

        self.issue_events([
            {'id': 'did:web:testserver:unknown'},
            {'id': product.did},
        ])

        self.assertIsNone(self.call_kwargs()['subject_did'])

    def test_a_first_event_that_names_a_product_is_linked(self):
        product = self.product_did()

        self.issue_events([{'id': product.did}])

        self.assertEqual(self.call_kwargs()['subject_did'], product)

    def test_an_empty_list_of_events_is_a_400(self):
        response = self.issue_events([])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'credentialSubject must be a non-empty list of events.',
        )
        self.issue.assert_not_called()

    def test_a_first_event_with_no_id_is_a_400(self):
        response = self.issue_events([{'eventType': 'repair'}])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['error'],
            'The first event in the list must have a valid "id".',
        )
        self.issue.assert_not_called()

    def test_a_subject_that_is_not_a_list_is_a_validation_error(self):
        response = self.post(ISSUE_PATHS['traceability'], {
            'schema_name': 'dte.json',
            'issuer_did': self.issuer.did,
            'credentialSubject': {'id': 'did:web:testserver:device-1'},
        })

        self.assertEqual(response.status_code, 422)

    def test_an_issuer_that_is_not_ours_is_refused_before_the_events_are_read(self):
        """The issuer is resolved first, so a bad batch from a stranger
        answers 403 and not 400."""
        response = self.issue_events([], issuer='did:web:elsewhere.example:issuer')

        self.assertEqual(response.status_code, 403)
        self.issue.assert_not_called()

    def test_the_endpoint_needs_a_token(self):
        response = self.client.post(
            ISSUE_PATHS['traceability'],
            data=json.dumps({
                'schema_name': 'dte.json',
                'issuer_did': self.issuer.did,
                'credentialSubject': [{'id': 'did:web:testserver:device-1'}],
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)


class ActiveUntpSchemasTest(ApiTestCase):
    """GET schemas/untp/active/: the three buckets the client picks from."""

    def get_schemas(self):
        response = self.client.get(SCHEMAS_PATH, **self.bearer())
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_with_no_schemas_the_three_buckets_are_empty(self):
        self.assertEqual(self.get_schemas(), {'dpp': [], 'dte': [], 'dfr': []})

    def test_each_untp_type_lands_in_its_own_bucket(self):
        untp_schema('dpp.json', ['VerifiableCredential', 'DigitalProductPassport'])
        untp_schema('dte.json', ['VerifiableCredential', 'DigitalTraceabilityEvent'])
        untp_schema('dfr.json', ['VerifiableCredential', 'DigitalFacilityRecord'])

        body = self.get_schemas()

        self.assertEqual([s['file_schema'] for s in body['dpp']], ['dpp.json'])
        self.assertEqual([s['file_schema'] for s in body['dte']], ['dte.json'])
        self.assertEqual([s['file_schema'] for s in body['dfr']], ['dfr.json'])

    def test_a_schema_that_is_not_untp_is_left_out(self):
        factories.make_schema('membership-card.json')

        self.assertEqual(self.get_schemas(), {'dpp': [], 'dte': [], 'dfr': []})

    def test_a_conformity_credential_is_untp_but_fits_in_no_bucket(self):
        """is_untp knows the fourth UNTP type; this endpoint does not.

        Schemas.is_untp answers for DigitalConformityCredential too, so the
        schema passes the filter and is then matched against three names that
        do not include it: it is silently dropped. Either the model knows a
        type the API cannot serve, or a 'dcc' bucket is missing.
        """
        untp_schema('dcc.json', ['VerifiableCredential', 'DigitalConformityCredential'])

        self.assertEqual(self.get_schemas(), {'dpp': [], 'dte': [], 'dfr': []})

    def test_the_name_is_the_file_name_and_not_the_name_of_the_schema(self):
        untp_schema('dpp.json', ['DigitalProductPassport'])

        entry = self.get_schemas()['dpp'][0]

        self.assertEqual(entry['name'], 'dpp.json')
        self.assertEqual(entry['name'], entry['file_schema'])

    def test_the_description_is_served_with_its_json_quotes(self):
        """B10 reaching the API: _description is read raw, so it arrives
        quoted the way json.dumps left it."""
        untp_schema('dpp.json', ['DigitalProductPassport'], description='A passport')

        self.assertEqual(self.get_schemas()['dpp'][0]['description'], '"A passport"')

    def test_the_url_is_the_validation_url(self):
        schema = untp_schema('dpp.json', ['DigitalProductPassport'])

        self.assertEqual(
            self.get_schemas()['dpp'][0]['url'], schema.validation_url
        )


SIGN_PATH = '/api/v1/webhook/sign/'
VERIFY_PATH = '/api/v1/webhook/verify/'

SNAPSHOT_SCHEMA = 'device-snapshot-v1.json'

# What workbench-script posts: the snapshot of one machine. operator_id and
# the three command outputs are the keys webhook_issue rewrites.
SNAPSHOT = {
    'uuid': '0f2b2d57-6a14-4b94-8f5f-2b64f7a7d1c2',
    'type': 'hardwareList',
    'software': 'workbench-script',
    'timestamp': '2024-06-11T14:41:12Z',
    'operator_id': 'abcdefghij1234567890',
    'data': {'dmidecode': 'dmi output', 'inxi': 'inxi output',
             'smartctl': 'smartctl output'},
}

UNAUTHORIZED = {'detail': 'Unauthorized'}
OUT_OF_SERVICE = {'error': 'Temporary out of service'}


class WebhookSignTestCase(ApiTestCase):
    """POST webhook/sign/: what workbench-script calls to sign a snapshot.

    Nothing is patched: the subject is the credential that comes out, so the
    snapshot is really rendered, signed and validated against its schema.
    """

    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema(SNAPSHOT_SCHEMA)
        self.did = factories.make_did(label='Issuer')
        # The token owner is the user that issues, and encrypt_data() needs
        # the per-user key that make_user leaves unset.
        self.admin_user.set_encrypted_sensitive_data()
        self.admin_user.save()

    def snapshot(self, **changes):
        data = json.loads(json.dumps(SNAPSHOT))
        for key, value in changes.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        return data

    def sign(self, data=None, type=None, **extra):
        payload = {
            'type': self.schema.type if type is None else type,
            'data': self.snapshot() if data is None else data,
        }
        payload.update(extra)
        return self.post(SIGN_PATH, payload)

    def signed(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body['status'], 'success')
        return json.loads(body['data'])


class WebhookSignTest(WebhookSignTestCase):
    """The HTTP contract, one row per way of calling the endpoint.

    Two rows of the contract are left out on purpose: a token wrapped in
    quotes and a token with no owner. Both answer 401 today, but whether that
    is the intended behaviour is an open question for workbench-script, and a
    test would turn it into the norm. DatabaseTokenAuthTest already covers
    the no-owner case for the API as a whole.
    """

    def raw_post(self, body, **headers):
        return self.client.post(
            SIGN_PATH, data=body, content_type='application/json', **headers
        )

    def test_the_requests_that_never_reach_the_view(self):
        valid = json.dumps({'type': self.schema.type, 'data': SNAPSHOT})
        rows = [
            ('no authorization header', lambda: self.raw_post(valid),
             401, UNAUTHORIZED),
            ('no bearer prefix',
             lambda: self.raw_post(valid, HTTP_AUTHORIZATION=str(self.token.token)),
             401, UNAUTHORIZED),
            ('unknown token',
             lambda: self.raw_post(valid, **self.bearer('0cc7bb5a-1d7e-4f6e-9a0f-2b0d5e4a1c33')),
             401, UNAUTHORIZED),
            ('token that is not a uuid',
             lambda: self.raw_post(valid, **self.bearer('not-a-uuid')),
             401, UNAUTHORIZED),
            ('body that does not parse',
             lambda: self.raw_post('{not json', **self.bearer()),
             400, {'detail': 'Cannot parse request body'}),
        ]
        for label, call, status, body in rows:
            with self.subTest(label):
                response = call()
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json(), body)

        self.assertFalse(VerificableCredential.objects.exists())

    def test_a_get_is_405_in_plain_text(self):
        response = self.client.get(SIGN_PATH, **self.bearer())

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.content, b'Method not allowed')

    def test_the_payload_is_validated_by_pydantic(self):
        rows = [
            ('empty body', {}, ['body', 'payload', 'type'], 'missing'),
            ('no data', {'type': self.schema.type}, ['body', 'payload', 'data'], 'missing'),
            ('data that is not a dict', {'type': self.schema.type, 'data': [1]},
             ['body', 'payload', 'data'], 'dict_type'),
        ]
        for label, payload, loc, kind in rows:
            with self.subTest(label):
                response = self.post(SIGN_PATH, payload)
                self.assertEqual(response.status_code, 422)
                errors = response.json()['detail']
                self.assertIn((loc, kind), [(e['loc'], e['type']) for e in errors])

    def test_an_inactive_token_is_refused(self):
        self.token.active = False
        self.token.save()

        response = self.sign()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), UNAUTHORIZED)

    def test_a_token_owned_by_a_plain_user_is_refused(self):
        self.token.owner = self.user
        self.token.save()

        self.assertEqual(self.sign().status_code, 401)

    def test_without_the_encryption_key_the_service_is_out(self):
        self.set_key_dids(None)

        response = self.sign()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), OUT_OF_SERVICE)

    def test_an_owner_who_has_not_accepted_the_terms_takes_it_down_too(self):
        self.admin_user.accept_gdpr = False
        self.admin_user.save()

        response = self.sign()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), OUT_OF_SERVICE)

    def test_without_an_organization_did_there_is_nothing_to_sign_with(self):
        self.did.delete()

        response = self.sign()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'Invalid DID'})

    def test_a_did_that_belongs_to_a_user_is_not_borrowed(self):
        self.did.delete()
        factories.make_did(label='Wallet', user=self.user)

        self.assertEqual(self.sign().json(), {'error': 'Invalid DID'})

    def test_an_unknown_type_is_a_400_that_names_it(self):
        response = self.sign(type='NoSuchSchema')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {'error': "Invalid credential: Schema for type 'NoSuchSchema' not found."},
        )

    def test_a_snapshot_without_an_operator_can_never_be_signed(self):
        """The fallback for a missing operator_id is '--', and the schema asks
        operatorId for at least ten characters: the placeholder is the one
        value guaranteed to fail validation."""
        response = self.sign(data=self.snapshot(operator_id=None))

        self.assertEqual(response.status_code, 400)
        error = response.json()['error']
        self.assertTrue(
            error.startswith('The credential is not valid with this schema:'), error
        )
        self.assertIn("'--' is too short", error)
        self.assertFalse(VerificableCredential.objects.exists())

    def test_the_happy_path_answers_200_with_the_signed_credential(self):
        response = self.sign()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(response.json()), ['data', 'status'])
        self.assertIn('proof', self.signed(response))


class WebhookSignHappyPathTest(WebhookSignTestCase):
    """The shape of the credential that comes out, and what is stored."""

    def test_by_default_the_credential_is_stored(self):
        """save defaults to True and now does save: the old view read the
        None that issue() used to return as a failure."""
        vc = self.signed(self.sign())

        stored = VerificableCredential.objects.get()
        self.assertEqual(stored.status, VerificableCredential.Status.ISSUED)
        self.assertEqual(stored.schema, self.schema)
        self.assertEqual(stored.issuer_did, self.did)
        self.assertEqual(stored.user, self.admin_user)
        self.assertEqual(json.loads(self.admin_user.decrypt_data(stored.data)), vc)

    def test_asking_not_to_save_returns_the_credential_and_stores_nothing(self):
        vc = self.signed(self.sign(save=False))

        self.assertIn('proof', vc)
        self.assertFalse(VerificableCredential.objects.exists())

    def test_the_command_outputs_become_the_evidence_at_the_root(self):
        """W3C puts evidence at the root of the credential, not inside the
        subject, which is not what reading webhook_issue suggests: it writes
        the key into the snapshot that becomes the subject."""
        vc = self.signed(self.sign(save=False))

        self.assertEqual(
            [(e['type'], e['operation'], e['output'], e['timestamp'])
             for e in vc['evidence']],
            [('HardwareList', 'dmidecode', 'dmi output', SNAPSHOT['timestamp']),
             ('HardwareList', 'smartctl', 'smartctl output', SNAPSHOT['timestamp']),
             ('HardwareList', 'inxi', 'inxi output', SNAPSHOT['timestamp'])],
        )
        self.assertNotIn('evidence', vc['credentialSubject'])

    def test_the_raw_command_output_does_not_reach_the_subject(self):
        subject = self.signed(self.sign(save=False))['credentialSubject']

        self.assertEqual(
            sorted(subject),
            ['id', 'operatorId', 'software', 'timestamp', 'type', 'uuid'],
        )
        self.assertEqual(subject['uuid'], SNAPSHOT['uuid'])
        self.assertEqual(subject['software'], 'workbench-script')
        self.assertEqual(subject['timestamp'], SNAPSHOT['timestamp'])

    def test_the_underscored_operator_id_is_renamed_for_the_schema(self):
        subject = self.signed(self.sign(save=False))['credentialSubject']

        self.assertEqual(subject['operatorId'], SNAPSHOT['operator_id'])

    def test_a_snapshot_with_no_command_output_still_gets_three_evidences(self):
        vc = self.signed(self.sign(data=self.snapshot(data=None), save=False))

        self.assertEqual([e['output'] for e in vc['evidence']], ['""', '""', '""'])

    def test_the_credential_is_issued_to_the_issuer_itself(self):
        vc = self.signed(self.sign(save=False))

        self.assertEqual(vc['issuer']['id'], self.did.did)
        self.assertEqual(vc['credentialSubject']['id'], self.did.did)

    def test_the_id_is_a_fresh_uuid_under_the_request_host(self):
        first = self.signed(self.sign(save=False))['id']
        second = self.signed(self.sign(save=False))['id']

        pattern = (r'^http://testserver/credentials/'
                   r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$')
        self.assertRegex(first, pattern)
        self.assertRegex(second, pattern)
        self.assertNotEqual(first, second)


class WebhookSnapshotTypeTest(WebhookSignTestCase):
    """The rewrite of data.type: only the literal 'Snapshot' is touched."""

    def subject_type(self, **changes):
        vc = self.signed(self.sign(data=self.snapshot(**changes), save=False))
        return vc['credentialSubject']['type']

    def test_the_rewrite_table(self):
        rows = [
            ({'type': 'Snapshot', 'erase': True}, 'dataDeletion'),
            ({'type': 'Snapshot', 'erase': False}, 'hardwareList'),
            ({'type': 'Snapshot'}, 'hardwareList'),
            ({'type': 'hardwareList'}, 'hardwareList'),
            ({'type': 'dataDeletion'}, 'dataDeletion'),
            # erase only matters for 'Snapshot': it does not turn a
            # hardwareList into a dataDeletion.
            ({'type': 'hardwareList', 'erase': True}, 'hardwareList'),
        ]
        for changes, expected in rows:
            with self.subTest(**changes):
                self.assertEqual(self.subject_type(**changes), expected)

    def test_any_other_type_is_left_as_it_comes_and_the_schema_judges_it(self):
        response = self.sign(data=self.snapshot(type='snapshot'))

        self.assertEqual(response.status_code, 400)
        self.assertIn("'snapshot' is not one of", response.json()['error'])


class WebhookSchemeTest(WebhookSignTestCase):
    """The scheme of the domain the credential is rendered under."""

    def test_testserver_over_plain_http_is_http(self):
        vc = self.signed(self.sign(save=False))

        self.assertTrue(vc['id'].startswith('http://testserver/'), vc['id'])

    def test_a_secure_request_is_https(self):
        response = self.post(
            SIGN_PATH,
            {'type': self.schema.type, 'data': self.snapshot(), 'save': False},
            secure=True,
        )

        self.assertTrue(self.signed(response)['id'].startswith('https://testserver/'))

    def test_localhost_is_https_even_over_plain_http(self):
        with self.settings(ALLOWED_HOSTS=['testserver', 'localhost']):
            response = self.post(
                SIGN_PATH,
                {'type': self.schema.type, 'data': self.snapshot(), 'save': False},
                HTTP_HOST='localhost',
            )

        vc = self.signed(response)
        self.assertTrue(vc['id'].startswith('https://localhost/'), vc['id'])
        contexts = [c for c in vc['@context'] if isinstance(c, str)]
        self.assertFalse(
            [c for c in contexts if c.startswith('http://localhost')], contexts
        )


class WebhookSchemaLookupTest(WebhookSignTestCase):
    """The three lookups the type goes through, in this order:
    type__iexact, the same with the spaces removed, file_schema__icontains."""

    def test_the_type_is_matched_without_regard_to_case(self):
        self.signed(self.sign(type='devicesnapshotv1', save=False))

    def test_a_type_written_with_spaces_is_matched(self):
        self.signed(self.sign(type='Device Snapshot V1', save=False))

    def test_a_piece_of_the_file_name_is_matched(self):
        self.signed(self.sign(type='device-snapshot', save=False))

    def test_any_short_string_found_in_a_file_name_picks_a_schema(self):
        """The last lookup is a substring of the file name, so 'json' -or a
        single letter- matches every schema there is: the type stops meaning
        anything as soon as it is not an exact title."""
        for typ in ('json', 'e', '-'):
            with self.subTest(type=typ):
                self.signed(self.sign(type=typ, save=False))

    def test_a_loose_type_can_pick_a_schema_that_has_nothing_to_do(self):
        """With another schema on file, 'membership' signs the snapshot
        against the membership card: the error is a validation failure of the
        wrong schema, not the 'not found' the client would expect."""
        factories.make_schema('membership-card.json')

        response = self.sign(type='membership', save=False)

        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            response.json()['error'].startswith(
                'The credential is not valid with this schema:'
            ),
            response.json(),
        )


class WebhookVerifyTest(ApiTestCase):
    """POST webhook/verify/: a credential file, checked like the portal does.

    The file is validated with VerificationForm, whose rules are tested in
    test_verification_form.py; here it is enough that each one is applied and
    comes out as a 400 with the ErrorResponse shape. VerificationService is
    tested in test_services.py.
    """

    def setUp(self):
        super().setUp()
        # The SSRF guard resolves the hosts of @context and did:web: nothing
        # here should go out to the network.
        self.patched('idhub.services.VerificationService.validate_safe_host')

    def upload(self, name='credential.json', content=b'{}',
               content_type='application/json', token=None):
        return self.client.post(
            VERIFY_PATH,
            data={'file_import': SimpleUploadedFile(name, content, content_type=content_type)},
            **self.bearer(token),
        )

    def error(self, message):
        return {'error': message, 'details': None, 'path': None}

    def test_without_a_token_it_is_refused(self):
        response = self.client.post(VERIFY_PATH, data={
            'file_import': SimpleUploadedFile('c.json', b'{}', content_type='application/json'),
        })

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), UNAUTHORIZED)

    def test_without_the_encryption_key_the_service_is_out(self):
        self.set_key_dids(None)

        response = self.upload()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), self.error('Temporary out of service'))

    def test_an_owner_who_has_not_accepted_the_terms_takes_it_down_too(self):
        self.admin_user.accept_gdpr = False
        self.admin_user.save()

        self.assertEqual(self.upload().json(), self.error('Temporary out of service'))

    def test_a_request_with_no_file_is_a_422(self):
        response = self.client.post(VERIFY_PATH, data={}, **self.bearer())

        self.assertEqual(response.status_code, 422)
        errors = response.json()['detail']
        self.assertIn((['file', 'file_import'], 'missing'),
                      [(e['loc'], e['type']) for e in errors])

    def test_the_rules_of_the_verification_form_are_applied(self):
        rows = [
            ('too large',
             {'content': b'a' * (VerificationForm.MAX_UPLOAD_SIZE + 1)},
             'The file is too large. The maximum allowed size is 5MB.'),
            ('extension',
             {'name': 'credential.txt'},
             'Invalid file extension. Only .json, .pdf and .jwt are allowed.'),
            ('content type',
             {'content_type': 'image/png'},
             'Unsupported file format. Please upload a valid JSON, PDF, or JWT credential.'),
            ('not utf-8',
             {'content': b'\xff\xfe\x00'},
             'The file is not a valid UTF-8 encoded text file.'),
        ]
        verify = self.patched('idhub.api.api.VerificationService.verify_document')
        for label, kwargs, message in rows:
            with self.subTest(label):
                response = self.upload(**kwargs)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json(), self.error(message))
        verify.assert_not_called()

    def test_a_json_file_that_is_not_a_credential_is_a_200_that_says_so(self):
        response = self.upload(content=b'not json at all')

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body['is_valid'])
        self.assertEqual(
            [(s['name'], s['status']) for s in body['steps']],
            [('Format parsing', 'Failed')],
        )

    def signed_credential(self):
        user = self.user
        user.set_encrypted_sensitive_data()
        user.save()
        credential = factories.make_issued_credential(user)
        return json.loads(user.decrypt_data(credential.data))

    def test_a_credential_this_instance_signed_verifies(self):
        content = json.dumps(self.signed_credential()).encode()

        response = self.upload(content=content)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['is_valid'], body['steps'])
        self.assertTrue(body['steps'])
        self.assertEqual({s['status'] for s in body['steps']}, {'Success'})

    def test_a_tampered_credential_is_a_200_with_is_valid_false(self):
        credential = self.signed_credential()
        credential['credentialSubject']['firstName'] = 'Tampered'

        response = self.upload(content=json.dumps(credential).encode())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body['is_valid'])
        self.assertIn(('Cryptographic Integrity', 'Failed'),
                      [(s['name'], s['status']) for s in body['steps']])

    def test_a_pdf_goes_to_the_eidas1_branch(self):
        verify_pdf = self.patched(
            'idhub.api.api.VerificationService.verify_pdf',
            return_value={**VerificationService.empty_results(), 'is_valid': True},
        )
        verify_document = self.patched(
            'idhub.api.api.VerificationService.verify_document'
        )
        content = b'%PDF-1.4\xff\xfe binary'

        rows = (('signed.pdf', 'application/pdf', content),
                ('signed.pdf', 'application/octet-stream', content),
                # The content type alone also routes to the PDF branch.
                ('signed.json', 'application/pdf', b'%PDF-1.4 text only'))
        for name, content_type, body in rows:
            with self.subTest(name=name, content_type=content_type):
                verify_pdf.reset_mock()
                response = self.upload(name=name, content=body,
                                       content_type=content_type)
                self.assertEqual(response.status_code, 200, response.content)
                self.assertTrue(response.json()['is_valid'])
                verify_pdf.assert_called_once_with(body)

        verify_document.assert_not_called()

    def test_a_binary_file_named_json_is_refused_even_if_it_says_pdf(self):
        """The form checks UTF-8 by extension, before the content type
        decides the branch: a .json is always text, whatever it claims. The
        inline checks this endpoint had before sent it to verify_pdf."""
        verify_pdf = self.patched('idhub.api.api.VerificationService.verify_pdf')

        response = self.upload(name='signed.json', content=b'%PDF-1.4\xff\xfe',
                               content_type='application/pdf')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            self.error('The file is not a valid UTF-8 encoded text file.'),
        )
        verify_pdf.assert_not_called()
