"""Tests for the UNTP issuance chain.

Three pieces, in the order a request goes through them:

- ``CredentialIssuanceService.issue_untp_credential`` (idhub/services.py:23),
  which is what the v1 API delegates to. idhub/tests/test_api.py patches it by
  name, so until now nobody checked that what it signs is a UNTP credential at
  all; these tests are the other half of that contract.
- ``VerificableCredential.render_untp`` and its six helpers
  (idhub/models.py:1139-1248), which build the document out of the schema, the
  organization and the issuer DID, and hand it to the pydantic models of
  idhub/templates/untp_models.py.
- ``VerificableCredential.generate_enveloped_jwt`` (idhub/models.py:1251),
  which wraps that document in a signed JWT for the ?format=jwt download of
  idhub/admin/views.py:731.

No UNTP schema ships in settings.SCHEMAS_DIR, so they are built here. Only a
handful of keys matter to this code -``properties.type.default`` and
``properties.@context.default``- and spelling them out in each test is what
documents which ones.

The signing of the JWT is real Ed25519, which needs no network. The signing
inside the service is not: it would make pyvckit fetch the UNTP JSON-LD
contexts, so ``verify_schema`` and ``issue`` are patched by name there, and an
unforeseen call fails loudly instead of going out to the internet.
"""

import copy
import json

from unittest.mock import patch

import jwt as pyjwt

from django.test import override_settings
from jwt.algorithms import get_default_algorithms
from oidc4vp.models import Organization

from idhub.models import DID, Schemas, VerificableCredential
from idhub.services import CredentialIssuanceService
from test_support import factories
from test_support.base import IdHubTestCase


DPP_CONTEXT = 'https://test.uncefact.org/vocabulary/untp/dpp/0.6.0/'
W3C_V2 = 'https://www.w3.org/ns/credentials/v2'
JWS_SUITE = 'https://w3id.org/security/suites/jws-2020/v1'
SECURITY_V2 = 'https://w3id.org/security/v2'

SCHEMA_SKELETON = {
    'title': 'DigitalProductPassport',
    'name': 'Product passport',
    'description': 'A passport',
    'properties': {
        'type': {'default': ['DigitalProductPassport', 'VerifiableCredential']},
        '@context': {'default': [W3C_V2, DPP_CONTEXT]},
    },
}


class UntpTestCase(IdHubTestCase):
    def untp_schema(self, file_name='dpp.json', properties=None, **fields):
        """A schema row Schemas.is_untp answers for.

        ``properties`` overrides entries of properties; a None value drops the
        entry, which is how a schema that declares no @context is built.
        """
        data = copy.deepcopy(SCHEMA_SKELETON)
        for key, value in (properties or {}).items():
            if value is None:
                data['properties'].pop(key, None)
            else:
                data['properties'][key] = value
        return Schemas.objects.create(
            file_schema=file_name, data=json.dumps(data), **fields
        )

    def credential(self, schema=None, issuer_did=None, json_data=None, **fields):
        cred = VerificableCredential(
            verified=True,
            user=self.admin_user,
            json_data=json_data if json_data is not None else {'productName': 'Widget'},
            issuer_did=issuer_did or factories.make_did(label='Issuer'),
            schema=schema or self.untp_schema(),
            type='DigitalProductPassport',
            **fields,
        )
        cred.save()
        return cred

    def web_did(self, label='Web issuer'):
        did = DID.objects.create(label=label, type=DID.Types.WEB.value)
        did.set_did()
        did.save()
        return did

    def rendered(self, cred, domain='https://testserver/', **kwargs):
        return json.loads(cred.render_untp(domain=domain, **kwargs))


class BaseUrlTest(UntpTestCase):
    """_get_base_url decides the host the credential says it lives on."""

    def test_a_didweb_issuer_imposes_its_own_host(self):
        """The domain the caller passes is ignored: a did:web credential has to
        be served from the host its DID resolves on."""
        cred = self.credential(issuer_did=self.web_did())
        self.assertEqual(cred._get_base_url('https://somewhere.else/'),
                         'https://testserver')

    def test_a_didweb_on_localhost_is_addressed_over_plain_http(self):
        did = self.web_did()
        did.did = 'did:web:localhost:abc'
        did.save()
        self.assertEqual(self.credential(issuer_did=did)._get_base_url('https://x/'),
                         'http://localhost')

    def test_any_other_issuer_falls_back_to_the_domain_given(self):
        cred = self.credential()
        self.assertEqual(cred._get_base_url('https://testserver/'),
                         'https://testserver')

    def test_a_did_too_short_to_carry_a_host_falls_back_too(self):
        did = factories.make_did(label='Issuer')
        did.did = 'did:web'
        did.save()
        self.assertEqual(self.credential(issuer_did=did)._get_base_url('https://x/'),
                         'https://x')

    def test_the_credential_url_hangs_off_the_base_url(self):
        cred = self.credential()
        self.assertEqual(
            cred._get_url_id('https://testserver'),
            'https://testserver/credentials/{}'.format(cred.vc_id),
        )


class IssuerPayloadTest(UntpTestCase):
    def test_the_issuer_is_the_did_and_the_name_of_the_main_organization(self):
        cred = self.credential()
        self.assertEqual(cred._get_issuer_payload(),
                         {'id': cred.issuer_did.did, 'name': self.org.name})

    def test_without_a_main_organization_the_name_is_empty(self):
        cred = self.credential()
        Organization.objects.all().delete()
        self.assertEqual(cred._get_issuer_payload(),
                         {'id': cred.issuer_did.did, 'name': ''})

    def test_a_webeth_issuer_is_named_by_its_ethereum_key(self):
        did = DID.objects.create(label='Eth', type=DID.Types.WEBETH.value,
                                 did='did:web:testserver:eth')
        did.set_key_material(json.dumps({'eth_issuer_pub_key': '0xabc'}))
        did.save()
        self.assertEqual(self.credential(issuer_did=did)._get_issuer_payload()['id'],
                         '0xabc')

    def test_a_webeth_issuer_without_a_key_keeps_its_did(self):
        did = DID.objects.create(label='Eth', type=DID.Types.WEBETH.value,
                                 did='did:web:testserver:eth')
        did.set_key_material(json.dumps({}))
        did.save()
        self.assertEqual(self.credential(issuer_did=did)._get_issuer_payload()['id'],
                         'did:web:testserver:eth')


class ContextListTest(UntpTestCase):
    """_get_unique_contexts builds the @context, deduplicated and in order."""

    def contexts(self, schema, domain='https://testserver/'):
        cred = self.credential(schema=schema)
        return cred._get_unique_contexts(domain, 'https://testserver')

    def test_the_schema_contexts_come_first_and_the_two_suites_last(self):
        self.assertEqual(self.contexts(self.untp_schema()),
                         [W3C_V2, DPP_CONTEXT, JWS_SUITE, SECURITY_V2])

    def test_the_w3c_v2_context_is_prepended_when_the_schema_omits_it(self):
        schema = self.untp_schema(properties={'@context': {'default': [DPP_CONTEXT]}})
        self.assertEqual(self.contexts(schema)[:2], [W3C_V2, DPP_CONTEXT])

    def test_a_context_declared_as_a_bare_string_is_wrapped(self):
        schema = self.untp_schema(properties={'@context': {'default': DPP_CONTEXT}})
        self.assertEqual(self.contexts(schema), [W3C_V2, DPP_CONTEXT, JWS_SUITE,
                                                 SECURITY_V2])

    def test_duplicates_inside_the_schema_are_collapsed(self):
        schema = self.untp_schema(
            properties={'@context': {'default': [DPP_CONTEXT, DPP_CONTEXT]}}
        )
        self.assertEqual(self.contexts(schema).count(DPP_CONTEXT), 1)

    def test_the_context_field_of_the_schema_is_appended(self):
        schema = self.untp_schema(context='https://absolute.example/ctx')
        self.assertEqual(self.contexts(schema)[2], 'https://absolute.example/ctx')

    def test_a_relative_context_field_is_resolved_against_the_base_url(self):
        schema = self.untp_schema(context='custom/ctx.jsonld')
        self.assertEqual(self.contexts(schema)[2],
                         'https://testserver/custom/ctx.jsonld')

    def test_a_context_field_already_in_the_list_is_not_repeated(self):
        schema = self.untp_schema(context=DPP_CONTEXT)
        self.assertEqual(self.contexts(schema), [W3C_V2, DPP_CONTEXT, JWS_SUITE,
                                                 SECURITY_V2])

    def test_a_schema_with_neither_context_falls_back_to_the_pilot_one(self):
        """With no @context default and no context field, what gets added is
        /context/base.jsonld -the context of the membership pilot-, which has
        nothing to do with UNTP."""
        schema = self.untp_schema(properties={'@context': None})
        self.assertEqual(self.contexts(schema),
                         [W3C_V2, 'https://testserver/context/base.jsonld',
                          JWS_SUITE, SECURITY_V2])

    def test_the_fallback_is_skipped_when_the_schema_declares_contexts(self):
        self.assertNotIn('https://testserver/context/base.jsonld',
                         self.contexts(self.untp_schema()))


class SchemaIdTest(UntpTestCase):
    def test_an_absolute_validation_url_is_used_as_is(self):
        schema = self.untp_schema(validation_url='https://explicit.example/s.json')
        self.assertEqual(self.credential(schema=schema)._resolve_schema_id('https://x/'),
                         'https://explicit.example/s.json')

    def test_a_local_schema_is_served_from_this_instance(self):
        cred = self.credential()
        self.assertEqual(cred._resolve_schema_id('https://testserver/'),
                         'https://testserver/schema/dpp.json')

    def test_a_remote_file_schema_arrives_through_the_validation_url(self):
        """Schemas.save() already copies an http file_schema into
        validation_url, so it is the first branch that answers."""
        schema = self.untp_schema(file_name='https://remote.example/s.json')
        self.assertEqual(schema.url, 'https://remote.example/s.json')
        self.assertEqual(self.credential(schema=schema)._resolve_schema_id('https://x/'),
                         'https://remote.example/s.json')

    def test_the_remote_file_schema_branch_needs_a_state_never_persisted(self):
        """The ``elif file_schema.startswith('http')`` branch is only reachable
        with an http file_schema and an empty validation_url, which save()
        never leaves behind."""
        schema = self.untp_schema(file_name='https://remote.example/s.json')
        schema.validation_url = ''
        self.assertEqual(self.credential(schema=schema)._resolve_schema_id('https://x/'),
                         'https://remote.example/s.json')


class CredentialSubjectTest(UntpTestCase):
    def test_the_context_of_the_subject_is_dropped(self):
        """The @context belongs to the credential, not to the subject."""
        cred = self.credential(json_data={'@context': ['x'], 'productName': 'W'})
        self.assertEqual(cred._prepare_credential_subject(), {'productName': 'W'})

    def test_the_stored_payload_is_left_untouched(self):
        cred = self.credential(json_data={'@context': ['x'], 'productName': 'W'})
        cred._prepare_credential_subject()
        self.assertIn('@context', cred.json_data)

    def test_every_item_of_a_list_of_subjects_is_cleaned(self):
        cred = self.credential(json_data=[{'@context': ['x'], 'a': 1},
                                          {'@context': ['y'], 'b': 2}])
        self.assertEqual(cred._prepare_credential_subject(), [{'a': 1}, {'b': 2}])

    def test_a_non_object_item_of_a_list_is_passed_through(self):
        cred = self.credential(json_data=[{'@context': ['x'], 'a': 1}, 'raw'])
        self.assertEqual(cred._prepare_credential_subject(), [{'a': 1}, 'raw'])

    def test_a_payload_that_is_neither_is_passed_through(self):
        cred = self.credential(json_data='scalar')
        self.assertEqual(cred._prepare_credential_subject(), 'scalar')


class RenderUntpTest(UntpTestCase):
    def test_the_whole_document_is_built_out_of_the_schema(self):
        cred = self.credential()
        doc = self.rendered(cred)
        self.assertEqual(doc['@context'], [W3C_V2, DPP_CONTEXT, JWS_SUITE, SECURITY_V2])
        self.assertEqual(doc['type'], ['DigitalProductPassport', 'VerifiableCredential'])
        self.assertEqual(doc['id'],
                         'https://testserver/credentials/{}'.format(cred.vc_id))
        self.assertEqual(doc['issuer'], {'type': ['CredentialIssuer'],
                                         'id': cred.issuer_did.did,
                                         'name': self.org.name})
        self.assertEqual(doc['credentialSubject'], {'productName': 'Widget'})
        self.assertEqual(doc['credentialSchema'],
                         {'type': 'https://w3id.org/security#FullJsonSchemaValidator2021',
                          'id': 'https://testserver/schema/dpp.json'})

    def test_the_issue_date_is_stamped_and_reported_in_zulu_time(self):
        cred = self.credential()
        self.assertIsNone(cred.issued_on)
        doc = self.rendered(cred)
        self.assertIsNotNone(cred.issued_on)
        self.assertEqual(doc['validFrom'],
                         cred.issued_on.strftime('%Y-%m-%dT%H:%M:%SZ'))

    def test_rendering_twice_keeps_the_first_issue_date(self):
        cred = self.credential()
        first = self.rendered(cred)['validFrom']
        self.assertEqual(self.rendered(cred)['validFrom'], first)

    def test_the_name_is_hardcoded_and_ignores_the_version_asked_for(self):
        """Every UNTP credential this project issues is called
        'Idhub UNTP 0.7.0  credential', double space included, whatever is
        passed as ``version``."""
        self.assertEqual(self.rendered(self.credential(), version='0.6.0')['name'],
                         'Idhub UNTP 0.7.0  credential')

    def test_a_list_of_subjects_survives_the_pydantic_model(self):
        cred = self.credential(json_data=[{'a': 1}, {'b': 2}])
        self.assertEqual(self.rendered(cred)['credentialSubject'], [{'a': 1}, {'b': 2}])

    def test_empty_fields_are_left_out_of_the_document(self):
        cred = self.credential()
        self.assertNotIn('issuerAlsoKnownAs', self.rendered(cred)['issuer'])

    def test_version_one_is_declared_unsupported(self):
        with self.assertRaises(NotImplementedError):
            self.credential().render_untp(domain='https://x/', version='1.0.0')

    def test_an_unknown_version_is_refused(self):
        with self.assertRaisesMessage(ValueError, 'Unsupported UNTP version: 9'):
            self.credential().render_untp(domain='https://x/', version='9')

    def test_a_refused_version_has_already_stamped_the_issue_date(self):
        """set_issue_date() runs before the version is looked at, so a call
        that raises still mutates the credential. Nothing saves it, so it only
        shows if the same instance is rendered again afterwards."""
        cred = self.credential()
        with self.assertRaises(ValueError):
            cred.render_untp(domain='https://x/', version='9')
        self.assertIsNotNone(cred.issued_on)

    def test_a_subject_that_is_not_an_object_is_refused_by_the_model(self):
        cred = self.credential(json_data='scalar')
        with self.assertRaises(Exception) as caught:
            cred.render_untp(domain='https://testserver/')
        self.assertIn('credentialSubject', str(caught.exception))


class EnvelopedJwtTest(UntpTestCase):
    def envelope(self, cred, domain='https://testserver'):
        return json.loads(cred.generate_enveloped_jwt(domain=domain))

    def token_of(self, envelope):
        prefix = 'data:application/vc+jwt,'
        vc_id = envelope['verifiableCredential']['id']
        self.assertTrue(vc_id.startswith(prefix), vc_id)
        return vc_id[len(prefix):]

    def public_key_of(self, did):
        jwk = json.loads(did.get_key_material())
        return get_default_algorithms()['EdDSA'].from_jwk(
            json.dumps({k: v for k, v in jwk.items() if k != 'd'})
        )

    def payload_of(self, cred, **kwargs):
        """Decodes the token checking the signature against the issuer key."""
        token = self.token_of(self.envelope(cred, **kwargs))
        return pyjwt.decode(token, self.public_key_of(cred.issuer_did),
                            algorithms=['EdDSA'])

    def test_the_result_is_a_w3c_enveloped_verifiable_credential(self):
        envelope = self.envelope(self.credential())
        self.assertEqual(envelope['verifiableCredential']['@context'], [W3C_V2])
        self.assertEqual(envelope['verifiableCredential']['type'],
                         'EnvelopedVerifiableCredential')

    def test_the_token_is_signed_by_the_issuer(self):
        cred = self.credential()
        self.assertEqual(self.payload_of(cred)['id'],
                         'https://testserver/credentials/{}'.format(cred.vc_id))

    def test_the_header_names_the_key_the_credential_was_signed_with(self):
        cred = self.credential()
        header = pyjwt.get_unverified_header(self.token_of(self.envelope(cred)))
        self.assertEqual(header, {'typ': 'vc+jwt', 'alg': 'EdDSA',
                                  'kid': '{}#owner'.format(cred.issuer_did.did)})

    def test_the_payload_carries_the_rendered_template(self):
        payload = self.payload_of(self.credential())
        render_method = payload['renderMethod']
        self.assertEqual(render_method[0]['type'], ['RenderTemplate2024'])
        self.assertIn('Widget', render_method[0]['template'])

    def test_the_issuer_of_the_envelope_loses_the_type_the_render_gave_it(self):
        """generate_enveloped_jwt overwrites raw_vc['issuer'] wholesale, so the
        ``type: ['CredentialIssuer']`` that render_untp puts there is gone from
        the signed token."""
        cred = self.credential()
        self.assertEqual(self.rendered(cred)['issuer']['type'], ['CredentialIssuer'])
        self.assertEqual(self.payload_of(cred)['issuer'],
                         {'id': cred.issuer_did.did, 'name': self.org.name})

    def test_without_a_main_organization_it_crashes_before_the_name_matters(self):
        """Both _get_issuer_payload and generate_enveloped_jwt go out of their
        way to tolerate a missing main organization (filter().first() plus a
        getattr default), but it buys nothing: DID.get_organization() is a bare
        get(main=True), so decrypting the issuer key dies first. Same bare get
        as B18, from the other side."""
        cred = self.credential()
        Organization.objects.all().delete()
        with self.assertRaises(Organization.DoesNotExist):
            cred.generate_enveloped_jwt(domain='https://testserver')

    def test_a_key_that_is_not_an_ed25519_jwk_is_reported(self):
        did = factories.make_did(label='Issuer')
        did.set_key_material('not a jwk')
        did.save()
        with self.assertRaisesMessage(ValueError, 'Failed to parse Ed25519 JWK'):
            self.credential(issuer_did=did).generate_enveloped_jwt()

    def test_a_credential_that_is_not_untp_is_signed_anyway_with_no_type(self):
        """``if not self.is_untp`` never fires: is_untp is a method, not a
        property, and a bound method is always truthy. So the guard is dead and
        a plain credential goes through render_untp, which asks the schema for
        UNTP types it does not have and gets an empty list. The result is a
        signed JWT whose ``type`` is [] -not even VerifiableCredential- handed
        out by the ?format=jwt download of idhub/admin/views.py:731."""
        schema = factories.make_schema('membership-card.json')
        self.assertFalse(schema.is_untp)
        cred = self.credential(schema=schema, json_data={'organisation': 'Test Org'})
        self.assertTrue(cred.is_untp)
        self.assertEqual(self.payload_of(cred)['type'], [])


@override_settings(DOMAIN='testserver')
class IssueUntpCredentialTest(UntpTestCase):
    """The service the v1 API delegates its three issue endpoints to."""

    def issue(self, schema_name='dpp.json', subject_data=None,
              credential_type=None, subject_did=None, issuer_did=None):
        return CredentialIssuanceService.issue_untp_credential(
            self.admin_user,
            schema_name,
            subject_data if subject_data is not None else {'productName': 'Widget'},
            credential_type or ['DigitalProductPassport'],
            subject_did,
            issuer_did or factories.make_did(label='Issuer'),
        )

    def patched(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def accept_the_schema(self):
        return self.patched('idhub.services.verify_schema', return_value=(True, None))

    def test_an_unknown_schema_is_an_unprocessable_entity(self):
        self.untp_schema()
        status, body = self.issue(schema_name='missing.json')
        self.assertEqual(status, 422)
        self.assertEqual(body, {'error': "Schema 'missing.json' does not exist."})

    def test_nothing_is_stored_when_the_schema_does_not_exist(self):
        self.untp_schema()
        self.issue(schema_name='missing.json')
        self.assertFalse(VerificableCredential.objects.exists())

    def test_a_document_the_schema_rejects_never_reaches_the_signing(self):
        self.untp_schema()
        self.patched('idhub.services.verify_schema', return_value=(False, 'bad shape'))
        signing = self.patched('idhub.models.sign')
        status, body = self.issue()
        self.assertEqual(status, 400)
        self.assertEqual(body, {'error': 'Schema validation failed prior to signing.',
                                'details': 'bad shape'})
        signing.assert_not_called()

    def test_a_failed_issuance_is_reported_with_its_reason(self):
        self.untp_schema()
        self.accept_the_schema()
        self.patched('idhub.models.VerificableCredential.issue',
                     return_value=(False, 'signature refused'))
        self.assertEqual(self.issue(), (400, {'error': 'Issuance failed',
                                              'details': 'signature refused'}))

    def test_a_credential_that_issues_is_returned_as_created(self):
        self.untp_schema()
        self.accept_the_schema()
        self.patched('idhub.models.VerificableCredential.issue',
                     return_value=(True, '{"signed": true}'))
        self.assertEqual(self.issue(), (201, {'credential': '{"signed": true}'}))

    def test_the_credential_is_built_out_of_what_the_caller_asked_for(self):
        self.untp_schema()
        self.accept_the_schema()
        issue = self.patched('idhub.models.VerificableCredential.issue',
                             return_value=(True, '{}'))
        subject_did = factories.make_did(label='Subject', user=self.user)
        issuer_did = factories.make_did(label='Issuer')
        self.issue(subject_data={'productName': 'Laptop'}, subject_did=subject_did,
                   issuer_did=issuer_did)
        self.assertEqual(issue.call_args.kwargs['did'], subject_did)
        self.assertEqual(issue.call_args.kwargs['domain'], 'https://testserver/')
        self.assertTrue(issue.call_args.kwargs['save'])

    def test_the_document_validated_is_the_untp_render(self):
        self.untp_schema()
        verify = self.accept_the_schema()
        self.patched('idhub.models.VerificableCredential.issue', return_value=(True, '{}'))
        self.issue(subject_data={'productName': 'Laptop'})
        document = json.loads(verify.call_args.args[0])
        self.assertEqual(document['type'],
                         ['DigitalProductPassport', 'VerifiableCredential'])
        self.assertEqual(document['credentialSubject'], {'productName': 'Laptop'})

    def test_the_schema_is_verified_for_real_outside_debug(self):
        self.untp_schema()
        verify = self.accept_the_schema()
        self.patched('idhub.models.VerificableCredential.issue', return_value=(True, '{}'))
        self.issue()
        self.assertTrue(verify.call_args.kwargs['verify'])

    @override_settings(DEBUG=True)
    def test_with_debug_on_the_schema_is_not_really_verified(self):
        self.untp_schema()
        verify = self.accept_the_schema()
        self.patched('idhub.models.VerificableCredential.issue', return_value=(True, '{}'))
        self.issue()
        self.assertFalse(verify.call_args.kwargs['verify'])

    def test_anything_unforeseen_is_an_internal_error(self):
        self.untp_schema()
        self.patched('idhub.services.verify_schema', side_effect=RuntimeError('boom'))
        self.assertEqual(
            self.issue(),
            (500, {'error': 'Internal server error during credential issuance.'}),
        )

    def test_a_subject_payload_the_model_refuses_is_an_internal_error(self):
        """A scalar subject makes the pydantic model raise inside render, which
        the blanket except turns into a 500. The v1 API cannot send one -its
        schema forces an object or a list- so this is the shape of the failure
        for any other caller."""
        self.untp_schema()
        status, _body = self.issue(subject_data='scalar')
        self.assertEqual(status, 500)

    def test_the_validator_iri_rewrite_cannot_change_anything(self):
        """The service opens by rewriting a bare 'FullJsonSchemaValidator2021'
        into its absolute IRI, 'to satisfy strict JSON-LD validators'. Neither
        branch can fire -Schemas has no schema_type field, and its ``type``
        holds the credential type, which save() fills from the title- and even
        when forced, render_untp never reads it: CredentialSchema carries the
        absolute IRI as its own default."""
        schema = self.untp_schema()
        self.assertFalse(hasattr(schema, 'schema_type'))
        self.assertEqual(schema.type, 'DigitalProductPassport')

        schema.type = 'FullJsonSchemaValidator2021'
        schema.save()
        verify = self.accept_the_schema()
        self.patched('idhub.models.VerificableCredential.issue', return_value=(True, '{}'))
        self.issue()

        document = json.loads(verify.call_args.args[0])
        self.assertEqual(document['credentialSchema']['type'],
                         'https://w3id.org/security#FullJsonSchemaValidator2021')
        self.assertEqual(Schemas.objects.get(pk=schema.pk).type,
                         'FullJsonSchemaValidator2021')
