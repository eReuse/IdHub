"""Tests for the services of idhub/services.py.

Most of the file is VerificationService, the engine behind the public
/verify/ portal: it takes the file somebody uploads -a JSON-LD credential, a
W3C enveloped JWT or a bare token- and returns the report the template
paints: the list of steps, the issuer, the verdict and the payload. It never
touches the database, so those tests are SimpleTestCase. The three network
edges are patched by name -``socket.getaddrinfo`` for the SSRF guard,
``verify_signature`` and ``verify_schema`` for pyvckit, and ``resolve_did``
for did resolution- so an unforeseen call fails loudly instead of going out
to the network. The JWT branch is exercised against real Ed25519 signatures,
which need no network at all.

The last classes cover DIDService, which keeps the service endpoint of a
product DID in step with its did document.
"""
import base64
import json
import socket

from unittest.mock import patch

import jwt

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from django.test import SimpleTestCase

from idhub.models import DID
from idhub.services import DIDService, VerificationService
from test_support.base import IdHubBaseTestCase
from test_support.factories import make_user


# Nothing is ever contacted: getaddrinfo is patched and the guard only reads
# the range of the address. These only need to stay outside the IANA
# special-purpose ranges, which rules out the documentation ranges of RFC 5737
# and RFC 3849: ipaddress reports those as not global, so the guard would
# refuse them and the "accepted" case could not be written.
PUBLIC_IP = '45.150.186.215'       # idhub.pangea.org
PUBLIC_IPV6 = '2606:2800:220:1:248:1893:25c8:1946'

REFUSED_ADDRESS = (
    'Access to private, loopback, or reserved network addresses is prohibited.'
)

KID = 'did:key:zTestKey#key-1'

UNTP_SCHEMA = 'https://untp.unece.org/artefacts/schema/v0.7.0'


def addrinfo(*ips):
    """What socket.getaddrinfo answers; the guard only reads item[4][0]."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in ips]


def jwk_of(private_key, padded=False):
    raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    x = base64.urlsafe_b64encode(raw).decode()
    return {'kty': 'OKP', 'crv': 'Ed25519', 'x': x if padded else x.rstrip('=')}


class PatchMixin:

    def patch(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def patch_resolver(self, *ips):
        resolver = self.patch('idhub.services.socket.getaddrinfo')
        resolver.return_value = addrinfo(*(ips or (PUBLIC_IP,)))
        return resolver

    def details(self, results):
        return [str(step['detail']) for step in results['steps']]

    def outcomes(self, results):
        return [(str(step['name']), step['status']) for step in results['steps']]


class ValidateSafeHostTest(PatchMixin, SimpleTestCase):
    """The anti-SSRF guard: resolve the name, refuse non-public addresses."""

    def setUp(self):
        self.resolver = self.patch('idhub.services.socket.getaddrinfo')

    def test_an_empty_host_is_refused_before_resolving(self):
        for host in ('', None):
            with self.subTest(host=host):
                with self.assertRaises(ValueError) as ctx:
                    VerificationService.validate_safe_host(host)
                self.assertEqual(str(ctx.exception), 'Host name cannot be empty.')
        self.resolver.assert_not_called()

    def test_a_public_address_is_accepted(self):
        self.resolver.return_value = addrinfo(PUBLIC_IP)
        self.assertIsNone(
            VerificationService.validate_safe_host('example.org')
        )

    def test_the_non_public_ranges_are_refused(self):
        for ip in (
            '10.0.0.1',
            '172.17.0.2',
            '192.168.1.1',
            '127.0.0.1',
            '169.254.1.1',
            '224.0.0.1',
            '0.0.0.0',
            '100.64.0.1',
            '::1',
            'fd00::1',
        ):
            with self.subTest(ip=ip):
                self.resolver.return_value = addrinfo(ip)
                with self.assertRaises(ValueError) as ctx:
                    VerificationService.validate_safe_host('somewhere.example.org')
                self.assertEqual(str(ctx.exception), REFUSED_ADDRESS)

    def test_a_single_non_public_answer_is_enough_to_refuse(self):
        # Every address the name resolves to is checked, not just the first.
        self.resolver.return_value = addrinfo(PUBLIC_IP, '127.0.0.1')
        with self.assertRaises(ValueError) as ctx:
            VerificationService.validate_safe_host('example.org')
        self.assertEqual(str(ctx.exception), REFUSED_ADDRESS)

    def test_a_name_that_does_not_resolve_is_refused(self):
        self.resolver.side_effect = socket.gaierror
        with self.assertRaises(ValueError) as ctx:
            VerificationService.validate_safe_host('nowhere.example.org')
        self.assertEqual(
            str(ctx.exception), "Unable to resolve host 'nowhere.example.org'."
        )

    def test_the_port_reaches_the_resolver(self):
        self.resolver.return_value = addrinfo(PUBLIC_IP)
        VerificationService.validate_safe_host('example.org', 8443)
        self.assertEqual(self.resolver.call_args.args[:2], ('example.org', 8443))

    def test_the_brackets_of_an_ipv6_literal_are_stripped(self):
        self.resolver.return_value = addrinfo(PUBLIC_IPV6)
        VerificationService.validate_safe_host('[{}]'.format(PUBLIC_IPV6))
        self.assertEqual(self.resolver.call_args.args[0], PUBLIC_IPV6)


class ValidateSafeDidTest(PatchMixin, SimpleTestCase):
    """Only did:web reaches the resolver, and only its domain segment."""

    def setUp(self):
        self.resolver = self.patch_resolver()

    def test_anything_that_is_not_a_did_web_goes_unchecked(self):
        for did in ('did:key:z6MkDummy', 'did:web', 'https://example.org', '',
                    None, 123, {}):
            with self.subTest(did=did):
                self.assertIsNone(VerificationService.validate_safe_did(did))
        self.resolver.assert_not_called()

    def test_the_domain_of_a_did_web_is_resolved(self):
        VerificationService.validate_safe_did('did:web:example.org')
        self.assertEqual(self.resolver.call_args.args[:2], ('example.org', 443))

    def test_the_path_segments_are_not_part_of_the_domain(self):
        VerificationService.validate_safe_did('did:web:example.org:a:b')
        self.assertEqual(self.resolver.call_args.args[:2], ('example.org', 443))

    def test_an_encoded_port_is_decoded_and_used(self):
        VerificationService.validate_safe_did('did:web:example.org%3A8443:a')
        self.assertEqual(self.resolver.call_args.args[:2], ('example.org', 8443))

    def test_a_non_public_domain_is_refused(self):
        self.resolver.return_value = addrinfo('127.0.0.1')
        with self.assertRaises(ValueError) as ctx:
            VerificationService.validate_safe_did('did:web:localhost')
        self.assertEqual(str(ctx.exception), REFUSED_ADDRESS)

    def test_the_malformed_did_message_is_unreachable(self):
        # Anything starting with "did:web:" splits into at least three parts,
        # so the len(parts) < 3 branch cannot be taken: an empty domain is
        # reported as an empty host instead of as a malformed did.
        with self.assertRaises(ValueError) as ctx:
            VerificationService.validate_safe_did('did:web:')
        self.assertEqual(str(ctx.exception), 'Host name cannot be empty.')


class ValidateSafeContextsTest(PatchMixin, SimpleTestCase):
    """The @context of the uploaded file, before pyld resolves it."""

    def setUp(self):
        self.resolver = self.patch_resolver()

    def hosts(self):
        return [call.args[0] for call in self.resolver.call_args_list]

    def test_a_single_url_given_as_a_string(self):
        VerificationService.validate_safe_contexts('https://example.org/c.jsonld')
        self.assertEqual(self.hosts(), ['example.org'])

    def test_every_url_of_a_list_is_checked_and_the_rest_ignored(self):
        VerificationService.validate_safe_contexts([
            'https://a.example.org/c',
            {'inline': 'term'},
            'https://b.example.org/c',
        ])
        self.assertEqual(self.hosts(), ['a.example.org', 'b.example.org'])

    def test_the_values_of_a_dict_are_checked(self):
        VerificationService.validate_safe_contexts({
            '@vocab': 'https://example.org/v#',
            '@version': 1.1,
        })
        self.assertEqual(self.hosts(), ['example.org'])

    def test_a_field_of_any_other_type_is_ignored(self):
        for field in (None, 1.1, True):
            with self.subTest(field=field):
                VerificationService.validate_safe_contexts(field)
        self.resolver.assert_not_called()

    def test_only_http_urls_are_checked(self):
        VerificationService.validate_safe_contexts([
            'ipfs://QmHash', '/context/base.jsonld', 'urn:example:vocab',
        ])
        self.resolver.assert_not_called()

    def test_the_default_port_follows_the_scheme(self):
        VerificationService.validate_safe_contexts('http://example.org/c')
        self.assertEqual(self.resolver.call_args.args[:2], ('example.org', 80))

    def test_an_explicit_port_is_used(self):
        VerificationService.validate_safe_contexts('https://example.org:9443/c')
        self.assertEqual(self.resolver.call_args.args[:2], ('example.org', 9443))

    def test_a_non_public_context_host_is_refused(self):
        self.resolver.return_value = addrinfo('10.0.0.5')
        with self.assertRaises(ValueError) as ctx:
            VerificationService.validate_safe_contexts(
                ['https://internal.example.org/c']
            )
        self.assertEqual(str(ctx.exception), REFUSED_ADDRESS)


class ReportTest(SimpleTestCase):
    """The shape of the dict the template reads."""

    def test_the_empty_report_is_invalid_and_has_no_steps(self):
        results = VerificationService.empty_results()
        self.assertEqual(results['steps'], [])
        self.assertIs(results['is_valid'], False)
        self.assertEqual(results['credential_type'], 'Unknown')
        for key in ('issuer_name', 'issuer_id', 'issuer_url', 'payload',
                    'html_template'):
            with self.subTest(key=key):
                self.assertIsNone(results[key])

    def test_a_step_records_the_outcome_as_a_word(self):
        results = VerificationService.empty_results()
        VerificationService.add_step(results, 'First', True, 'fine')
        VerificationService.add_step(results, 'Second', False, 'broken')
        self.assertEqual(results['steps'], [
            {'name': 'First', 'status': 'Success', 'detail': 'fine'},
            {'name': 'Second', 'status': 'Failed', 'detail': 'broken'},
        ])

    def test_each_report_owns_its_step_list(self):
        # A shared default would leak the steps of one verification into the
        # next, and the service is called once per request.
        first = VerificationService.empty_results()
        VerificationService.add_step(first, 'First', True, 'fine')
        self.assertEqual(VerificationService.empty_results()['steps'], [])


class FormatExceptionTest(SimpleTestCase):
    """Turning a nested library error into one readable line."""

    def test_a_remote_context_that_cannot_be_fetched_names_the_url(self):
        class JsonLdError(Exception):
            code = 'loading remote context failed'
            details = {'url': 'https://example.org/c.jsonld'}

        self.assertEqual(
            VerificationService._format_exception(JsonLdError()),
            'Failed to fetch remote JSON-LD context. The server might be down '
            'or inaccessible: https://example.org/c.jsonld',
        )

    def test_a_jsonld_error_with_a_cause_reports_the_type_of_the_cause(self):
        class JsonLdError(Exception):
            code = 'syntax error'
            details = {}
            cause = TypeError('boom')

        self.assertEqual(
            VerificationService._format_exception(JsonLdError()),
            'JSON-LD Parsing Error: TypeError',
        )

    def test_a_jsonld_error_without_a_cause_falls_back_to_its_message(self):
        class JsonLdError(Exception):
            code = 'syntax error'
            details = {}
            cause = None

        self.assertEqual(
            VerificationService._format_exception(JsonLdError('malformed @id')),
            'malformed @id',
        )

    def test_a_tuple_wrapped_message_is_unwrapped(self):
        self.assertEqual(
            VerificationService._format_exception(Exception(('boom',))), 'boom'
        )

    def test_only_the_first_line_survives(self):
        self.assertEqual(
            VerificationService._format_exception(ValueError('first\nsecond')),
            'first',
        )

    def test_a_plain_message_is_stripped(self):
        self.assertEqual(
            VerificationService._format_exception(ValueError('  plain  ')),
            'plain',
        )


class JwtVerifyKeyTest(SimpleTestCase):
    """Picking the verification key the token names out of the DID document."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.private_key = Ed25519PrivateKey.generate()
        cls.jwk = jwk_of(cls.private_key)

    def method(self, **overrides):
        return {'id': KID, 'publicKeyJwk': dict(self.jwk), **overrides}

    def test_a_document_without_verification_methods_is_refused(self):
        for document in (None, {}, {'id': 'did:key:zTestKey'}):
            with self.subTest(document=document):
                with self.assertRaises(ValueError) as ctx:
                    VerificationService._get_jwt_verify_key(KID, document)
                self.assertEqual(
                    str(ctx.exception), 'Invalid or empty DID Document provided.'
                )

    def test_the_method_whose_id_is_the_kid_is_used(self):
        document = {'verificationMethod': [
            self.method(id='did:key:zTestKey#other', publicKeyJwk={}),
            self.method(),
        ]}
        self.assertIsInstance(
            VerificationService._get_jwt_verify_key(KID, document),
            Ed25519PublicKey,
        )

    def test_the_fragment_alone_is_enough_to_match(self):
        document = {'verificationMethod': [
            self.method(id='did:key:zAnother#other', publicKeyJwk={}),
            self.method(id='did:web:other.example.org#key-1'),
        ]}
        self.assertIsInstance(
            VerificationService._get_jwt_verify_key(KID, document),
            Ed25519PublicKey,
        )

    def test_a_lone_method_is_used_even_when_the_kid_does_not_match(self):
        # With exactly one verification method the kid is not binding, so a
        # token may name a key the document does not list.
        document = {'verificationMethod': [self.method(id='did:key:zOther#zz')]}
        self.assertIsInstance(
            VerificationService._get_jwt_verify_key(KID, document),
            Ed25519PublicKey,
        )

    def test_no_match_among_several_methods_is_refused(self):
        document = {'verificationMethod': [
            self.method(id='did:key:zOne#a'),
            self.method(id='did:key:zTwo#b'),
        ]}
        with self.assertRaises(ValueError) as ctx:
            VerificationService._get_jwt_verify_key(KID, document)
        self.assertEqual(
            str(ctx.exception),
            "Verification key matching '{}' not found in the DID "
            'document.'.format(KID),
        )

    def test_a_jwk_without_the_x_coordinate_is_refused(self):
        document = {'verificationMethod': [self.method(publicKeyJwk={'kty': 'OKP'})]}
        with self.assertRaises(ValueError) as ctx:
            VerificationService._get_jwt_verify_key(KID, document)
        self.assertEqual(
            str(ctx.exception), "publicKeyJwk is missing the 'x' coordinate."
        )

    def test_a_multibase_key_is_not_supported(self):
        document = {'verificationMethod': [
            {'id': KID, 'publicKeyMultibase': 'z6MkDummy'},
        ]}
        with self.assertRaises(ValueError) as ctx:
            VerificationService._get_jwt_verify_key(KID, document)
        self.assertEqual(
            str(ctx.exception),
            "This verifier requires 'publicKeyJwk'. 'publicKeyMultibase' is "
            'not supported by this platform.',
        )

    def test_a_method_without_any_known_key_format_is_refused(self):
        document = {'verificationMethod': [{'id': KID, 'publicKeyPem': '---'}]}
        with self.assertRaises(ValueError) as ctx:
            VerificationService._get_jwt_verify_key(KID, document)
        self.assertEqual(
            str(ctx.exception),
            'Verification method contains unsupported key format.',
        )

    def test_the_padding_of_the_x_coordinate_is_optional(self):
        for padded in (True, False):
            with self.subTest(padded=padded):
                document = {'verificationMethod': [
                    self.method(publicKeyJwk=jwk_of(self.private_key, padded)),
                ]}
                self.assertIsInstance(
                    VerificationService._get_jwt_verify_key(KID, document),
                    Ed25519PublicKey,
                )

    def test_bytes_that_are_not_an_ed25519_key_are_refused(self):
        document = {'verificationMethod': [
            self.method(publicKeyJwk={'x': base64.urlsafe_b64encode(b'short').decode()}),
        ]}
        with self.assertRaises(ValueError) as ctx:
            VerificationService._get_jwt_verify_key(KID, document)
        self.assertIn(
            'Failed to parse Ed25519 public key bytes', str(ctx.exception)
        )


class InjectMissingSchemaTest(SimpleTestCase):
    """UNTP 0.7.0 credentials that ship no credentialSchema of their own."""

    def test_a_credential_that_declares_its_schema_is_left_alone(self):
        vc = {
            'type': ['DigitalProductPassport'],
            'credentialSchema': {'id': 'https://example.org/mine.json'},
        }
        injected = VerificationService._inject_untp_0_0_7_missing_schema(vc)
        self.assertEqual(
            injected['credentialSchema'], {'id': 'https://example.org/mine.json'}
        )

    def test_each_untp_type_gets_its_own_schema(self):
        for type_name, path in (
            ('DigitalProductPassport', 'dpp/DigitalProductPassport.json'),
            ('DigitalFacilityRecord', 'dfr/DigitalFacilityRecord.json'),
            ('DigitalTraceabilityEvent', 'dte/DigitalTraceabilityEvent.json'),
        ):
            with self.subTest(type=type_name):
                injected = VerificationService._inject_untp_0_0_7_missing_schema(
                    {'type': ['VerifiableCredential', type_name]}
                )
                self.assertEqual(injected['credentialSchema'], {
                    'type': 'https://w3id.org/security#FullJsonSchemaValidator2021',
                    'id': '{}/{}'.format(UNTP_SCHEMA, path),
                })

    def test_a_type_given_as_a_plain_string_is_honoured(self):
        injected = VerificationService._inject_untp_0_0_7_missing_schema(
            {'type': 'DigitalProductPassport'}
        )
        self.assertIn('credentialSchema', injected)

    def test_a_type_that_is_not_untp_gets_no_schema(self):
        for vc in ({'type': ['VerifiableCredential']}, {}):
            with self.subTest(vc=vc):
                injected = VerificationService._inject_untp_0_0_7_missing_schema(vc)
                self.assertNotIn('credentialSchema', injected)

    def test_the_credential_is_modified_in_place(self):
        vc = {'type': ['DigitalProductPassport']}
        self.assertIs(
            VerificationService._inject_untp_0_0_7_missing_schema(vc), vc
        )
        self.assertIn('credentialSchema', vc)


class ParseJsonTest(PatchMixin, SimpleTestCase):
    """Deciding what kind of document was uploaded."""

    def test_a_bare_token_is_wrapped_into_an_envelope(self):
        results = VerificationService.empty_results()
        doc = VerificationService._parse_json(
            '  eyJhbGciOiJFZERTQSJ9.e30.sig  ', results
        )
        self.assertEqual(doc, {
            'type': 'EnvelopedVerifiableCredential',
            'id': 'data:application/vc+jwt,eyJhbGciOiJFZERTQSJ9.e30.sig',
        })
        self.assertEqual(self.details(results), ['Raw JWT string loaded.'])

    def test_the_prefix_alone_makes_it_a_token(self):
        # Nothing is decoded at this point, so any string beginning with "eyJ"
        # is taken for a token and only fails further down.
        results = VerificationService.empty_results()
        doc = VerificationService._parse_json('eyJ-not-a-token', results)
        self.assertTrue(doc['id'].endswith('eyJ-not-a-token'))
        self.assertEqual(self.outcomes(results), [('Format parsing', 'Success')])

    def test_a_plain_credential_is_returned_untouched(self):
        results = VerificationService.empty_results()
        doc = VerificationService._parse_json('{"type": ["VerifiableCredential"]}',
                                              results)
        self.assertEqual(doc, {'type': ['VerifiableCredential']})
        self.assertEqual(self.details(results), ['Valid JSON document loaded.'])

    def test_a_wrapped_credential_is_unwrapped_and_marked(self):
        results = VerificationService.empty_results()
        doc = VerificationService._parse_json(
            json.dumps({'verifiableCredential': {'id': 'urn:vc'}}), results
        )
        self.assertEqual(doc, {'id': 'urn:vc', '_was_unwrapped': True})

    def test_a_file_that_is_not_json_is_reported(self):
        results = VerificationService.empty_results()
        self.assertIsNone(VerificationService._parse_json('not json', results))
        self.assertEqual(
            self.outcomes(results), [('Format parsing', 'Failed')]
        )
        self.assertEqual(self.details(results), ['Invalid JSON or JWT file.'])

    def test_a_presentation_holding_several_credentials_is_reported_as_bad_json(self):
        # The W3C shape of a presentation is an array, and the unwrapping
        # writes its marker into it: the TypeError lands in the same except as
        # a parse error, so the report ends up with two contradictory
        # "Format parsing" steps and the user is told the file is not JSON.
        results = VerificationService.empty_results()
        raw = json.dumps({
            'type': ['VerifiablePresentation'],
            'verifiableCredential': [{'id': 'urn:one'}, {'id': 'urn:two'}],
        })
        self.assertIsNone(VerificationService._parse_json(raw, results))
        self.assertEqual(self.outcomes(results), [
            ('Format parsing', 'Success'),
            ('Format parsing', 'Failed'),
        ])
        self.assertEqual(self.details(results)[-1], 'Invalid JSON or JWT file.')


class UnwrapAndVerifyTest(PatchMixin, SimpleTestCase):
    """The JSON-LD Data Integrity branch."""

    def setUp(self):
        self.verify_signature = self.patch(
            'idhub.services.verify_signature', return_value=(True, 'ok')
        )
        self.safe_host = self.patch(
            'idhub.services.VerificationService.validate_safe_host'
        )

    def credential(self, **overrides):
        doc = {
            '@context': ['https://www.w3.org/ns/credentials/v2'],
            'type': ['VerifiableCredential', 'DigitalProductPassport'],
            'issuer': {'id': 'did:web:issuer.example.org', 'name': 'Issuer'},
            'proof': {
                'type': 'DataIntegrityProof',
                'verificationMethod': 'did:web:issuer.example.org#key-1',
            },
        }
        doc.update(overrides)
        return doc

    def unwrap(self, doc, raw=None):
        results = VerificationService.empty_results()
        trusted = VerificationService._unwrap_and_verify(
            doc, raw if raw is not None else json.dumps(doc), results
        )
        return trusted, results

    def test_a_document_with_neither_proof_nor_envelope_is_reported(self):
        trusted, results = self.unwrap({'type': ['VerifiableCredential']})
        self.assertIsNone(trusted)
        self.assertEqual(self.outcomes(results), [('Type detection', 'Failed')])
        self.assertEqual(
            self.details(results), ['Missing proof block or enveloped JWT URI.']
        )

    def test_a_valid_signature_returns_the_credential_and_names_its_types(self):
        trusted, results = self.unwrap(self.credential())
        self.assertIsNotNone(trusted)
        self.assertEqual(
            results['credential_type'],
            'JSON-LD Data Integrity (VerifiableCredential, DigitalProductPassport)',
        )
        self.assertEqual(self.outcomes(results),
                         [('Cryptographic Integrity', 'Success')])

    def test_the_bytes_that_were_uploaded_are_what_gets_verified(self):
        # Re-serialising would change the digest, so the raw string is passed
        # through untouched.
        raw = '{"spacing": "preserved"}'
        self.unwrap(self.credential(), raw=raw)
        self.assertEqual(self.verify_signature.call_args.args, (raw,))

    def test_an_unwrapped_credential_is_reserialised_without_the_marker(self):
        doc = self.credential(_was_unwrapped=True)
        self.unwrap(doc, raw='{"the": "presentation"}')
        verified = json.loads(self.verify_signature.call_args.args[0])
        self.assertNotIn('_was_unwrapped', verified)
        self.assertEqual(verified['type'], doc['type'])

    def test_a_broken_signature_is_reported_with_its_reason(self):
        self.verify_signature.return_value = (False, 'digest mismatch')
        trusted, results = self.unwrap(self.credential())
        self.assertIsNone(trusted)
        self.assertEqual(self.outcomes(results),
                         [('Cryptographic Integrity', 'Failed')])
        self.assertEqual(
            self.details(results),
            ['Signature verification failed: digest mismatch'],
        )

    def test_a_single_type_given_as_a_string_is_listed_on_its_own(self):
        doc = self.credential(type='DigitalProductPassport')
        _trusted, results = self.unwrap(doc)
        self.assertEqual(results['credential_type'],
                         'JSON-LD Data Integrity (DigitalProductPassport)')

    def test_a_credential_without_contexts_only_checks_the_proof(self):
        doc = self.credential()
        del doc['@context']
        _trusted, results = self.unwrap(doc)
        self.assertEqual([call.args[0] for call in self.safe_host.call_args_list],
                         ['issuer.example.org'])
        self.assertEqual(self.outcomes(results),
                         [('Cryptographic Integrity', 'Success')])

    def test_the_contexts_and_the_did_of_the_proof_are_checked(self):
        self.unwrap(self.credential())
        self.assertEqual(
            [call.args[0] for call in self.safe_host.call_args_list],
            ['www.w3.org', 'issuer.example.org'],
        )

    def test_the_issuer_is_checked_when_the_proof_names_no_method(self):
        self.unwrap(self.credential(proof={'type': 'DataIntegrityProof'}))
        self.assertEqual(self.safe_host.call_args.args[0], 'issuer.example.org')

    def test_an_issuer_given_as_a_string_is_understood(self):
        doc = self.credential(
            issuer='did:web:plain.example.org', proof={'type': 'DataIntegrityProof'}
        )
        self.unwrap(doc)
        self.assertEqual(self.safe_host.call_args.args[0], 'plain.example.org')

    def test_a_refused_address_is_reported_instead_of_raised(self):
        self.safe_host.side_effect = ValueError(REFUSED_ADDRESS)
        trusted, results = self.unwrap(self.credential())
        self.assertIsNone(trusted)
        self.assertEqual(self.outcomes(results),
                         [('Cryptographic Integrity', 'Failed')])
        self.assertEqual(self.details(results), [REFUSED_ADDRESS])
        self.verify_signature.assert_not_called()

    def test_an_exception_from_the_library_is_reported_instead_of_raised(self):
        self.verify_signature.side_effect = Exception(('boom',))
        trusted, results = self.unwrap(self.credential())
        self.assertIsNone(trusted)
        self.assertEqual(self.details(results), ['boom'])

    def test_an_envelope_is_routed_to_the_jwt_branch(self):
        branch = self.patch(
            'idhub.services.VerificationService._verify_jwt_branch',
            return_value={'routed': True},
        )
        for doc in (
            {'type': ['EnvelopedVerifiableCredential']},
            {'id': 'data:application/vc+jwt,eyJ0.e30.sig'},
        ):
            with self.subTest(doc=doc):
                trusted, _results = self.unwrap(doc)
                self.assertEqual(trusted, {'routed': True})
        self.assertEqual(branch.call_count, 2)
        self.verify_signature.assert_not_called()


class VerifyJwtBranchTest(PatchMixin, SimpleTestCase):
    """The enveloped JWT branch, against real Ed25519 signatures."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.private_key = Ed25519PrivateKey.generate()
        cls.other_key = Ed25519PrivateKey.generate()
        cls.did_document = {
            'verificationMethod': [
                {'id': KID, 'publicKeyJwk': jwk_of(cls.private_key)},
            ],
        }

    def setUp(self):
        self.resolve_did = self.patch(
            'idhub.services.resolve_did', return_value=self.did_document
        )

    CREDENTIAL = {
        'type': ['VerifiableCredential', 'DigitalProductPassport'],
        'issuer': {'id': 'did:key:zTestKey', 'name': 'Issuer'},
        'credentialSubject': {'id': 'did:web:product.example.org'},
    }

    def envelope(self, claims, key=None, headers=None):
        token = jwt.encode(
            claims,
            key or self.private_key,
            algorithm='EdDSA',
            headers={'kid': KID} if headers is None else headers,
        )
        return {'id': 'data:application/vc+jwt,' + token}

    def verify(self, doc):
        results = VerificationService.empty_results()
        return VerificationService._verify_jwt_branch(doc, results), results

    def credential(self, **overrides):
        return dict(self.CREDENTIAL, **overrides)

    def test_a_signed_credential_is_accepted_and_typed(self):
        trusted, results = self.verify(
            self.envelope({'vc': self.credential()})
        )
        self.assertEqual(trusted['credentialSubject'],
                         self.CREDENTIAL['credentialSubject'])
        self.assertEqual(
            results['credential_type'],
            'W3C Enveloped JWT (VerifiableCredential, DigitalProductPassport)',
        )
        self.assertEqual(self.outcomes(results), [
            ('JWT Extraction', 'Success'),
            ('Cryptographic Integrity', 'Success'),
        ])

    def test_an_id_that_is_not_a_data_uri_is_reported(self):
        trusted, results = self.verify({'id': 'urn:not:a:data:uri'})
        self.assertIsNone(trusted)
        self.assertEqual(self.outcomes(results), [('JWT Extraction', 'Failed')])
        self.assertEqual(self.details(results), ['Invalid Data URI format.'])

    def test_a_token_without_a_kid_is_reported(self):
        trusted, results = self.verify(
            self.envelope({'vc': self.credential()}, headers={})
        )
        self.assertIsNone(trusted)
        self.assertEqual(
            self.details(results)[-1], "Missing 'kid' parameter in JWT header."
        )

    def test_an_issuer_whose_did_does_not_resolve_is_reported(self):
        self.resolve_did.return_value = None
        trusted, results = self.verify(self.envelope({'vc': self.credential()}))
        self.assertIsNone(trusted)
        self.assertEqual(
            self.details(results)[-1],
            'Failed to resolve DID Document for issuer: did:key:zTestKey',
        )

    def test_a_token_signed_with_another_key_is_reported_as_tampered(self):
        trusted, results = self.verify(
            self.envelope({'vc': self.credential()}, key=self.other_key)
        )
        self.assertIsNone(trusted)
        self.assertEqual(self.outcomes(results)[-1],
                         ('Cryptographic Integrity', 'Failed'))
        self.assertEqual(
            self.details(results)[-1],
            'Signature verification failed. The data was tampered with.',
        )

    def test_an_expired_credential_is_reported(self):
        trusted, results = self.verify(self.envelope({
            'vc': self.credential(validUntil='2000-01-01T00:00:00Z'),
        }))
        self.assertIsNone(trusted)
        self.assertEqual(self.details(results)[-1],
                         'The credential has expired.')

    def test_a_credential_that_is_not_yet_valid_is_reported(self):
        trusted, results = self.verify(self.envelope({
            'vc': self.credential(validFrom='2999-01-01T00:00:00Z'),
        }))
        self.assertIsNone(trusted)
        self.assertEqual(self.details(results)[-1],
                         'The credential is not yet valid.')

    def test_a_credential_inside_its_validity_window_is_accepted(self):
        trusted, results = self.verify(self.envelope({
            'vc': self.credential(
                type='DigitalProductPassport',
                validFrom='2000-01-01T00:00:00Z',
                validUntil='2999-01-01T00:00:00Z',
            ),
        }))
        self.assertIsNotNone(trusted)
        self.assertEqual(self.outcomes(results)[-1],
                         ('Cryptographic Integrity', 'Success'))
        self.assertEqual(results['credential_type'],
                         'W3C Enveloped JWT (DigitalProductPassport)')

    def test_the_1_1_date_fields_are_honoured_too(self):
        trusted, results = self.verify(self.envelope({
            'vc': self.credential(expirationDate='2000-01-01T00:00:00Z'),
        }))
        self.assertIsNone(trusted)
        self.assertEqual(self.details(results)[-1],
                         'The credential has expired.')

    def test_only_one_spelling_of_the_dates_is_accepted(self):
        # Both of these are valid XSD dateTimes, which is what the data model
        # asks for, but the branch parses with a fixed "...%SZ" format: a
        # cryptographically sound credential is reported as a verification
        # failure, with the raw strptime message as the detail.
        for value in ('2999-01-01T00:00:00+00:00', '2999-01-01T00:00:00.000Z'):
            with self.subTest(value=value):
                trusted, results = self.verify(self.envelope({
                    'vc': self.credential(validUntil=value),
                }))
                self.assertIsNone(trusted)
                self.assertEqual(self.outcomes(results)[-1],
                                 ('Verification Process', 'Failed'))
                self.assertIn('does not match format',
                              self.details(results)[-1])

    def test_a_payload_without_a_vc_claim_is_taken_whole(self):
        trusted, _results = self.verify(self.envelope(self.credential()))
        self.assertEqual(trusted['credentialSubject'],
                         self.CREDENTIAL['credentialSubject'])

    def test_an_empty_vc_claim_is_reported(self):
        trusted, results = self.verify(self.envelope({'vc': {}}))
        self.assertIsNone(trusted)
        self.assertEqual(
            self.details(results)[-1],
            'The token is mathematically valid, but the payload is empty.',
        )

    def test_the_issuer_did_and_the_payload_contexts_are_checked(self):
        safe_host = self.patch(
            'idhub.services.VerificationService.validate_safe_host'
        )
        web_kid = 'did:web:issuer.example.org#key-1'
        self.resolve_did.return_value = {'verificationMethod': [
            {'id': web_kid, 'publicKeyJwk': jwk_of(self.private_key)},
        ]}
        doc = self.envelope(
            {'vc': self.credential(**{
                '@context': ['https://www.w3.org/ns/credentials/v2'],
            })},
            headers={'kid': web_kid},
        )
        trusted, _results = self.verify(doc)
        self.assertIsNotNone(trusted)
        self.assertEqual(
            [call.args[0] for call in safe_host.call_args_list],
            ['issuer.example.org', 'www.w3.org'],
        )


class ExtractIssuerTest(SimpleTestCase):
    """Who issued it, and whether the portal can link to them."""

    def extract(self, issuer):
        results = VerificationService.empty_results()
        VerificationService._extract_issuer({'issuer': issuer}, results)
        return results

    def test_an_issuer_object_gives_a_name_and_an_id(self):
        results = self.extract({'id': 'did:web:a.example.org', 'name': 'Acme'})
        self.assertEqual(results['issuer_name'], 'Acme')
        self.assertEqual(results['issuer_id'], 'did:web:a.example.org')

    def test_an_issuer_given_as_a_string_has_no_name(self):
        results = self.extract('did:web:a.example.org')
        self.assertIsNone(results['issuer_name'])
        self.assertEqual(results['issuer_id'], 'did:web:a.example.org')

    def test_only_an_http_id_becomes_a_link(self):
        self.assertEqual(
            self.extract('https://a.example.org/me')['issuer_url'],
            'https://a.example.org/me',
        )
        for issuer in ('did:web:a.example.org', 'did:key:z6MkDummy', ''):
            with self.subTest(issuer=issuer):
                self.assertIsNone(self.extract(issuer)['issuer_url'])

    def test_a_credential_with_no_issuer_leaves_the_three_fields_empty(self):
        results = VerificationService.empty_results()
        VerificationService._extract_issuer({}, results)
        self.assertIsNone(results['issuer_name'])
        self.assertIsNone(results['issuer_id'])
        self.assertIsNone(results['issuer_url'])


class ExtractRenderMethodTest(SimpleTestCase):
    """The template a credential carries for its own presentation."""

    def extract(self, vc, is_valid=True):
        results = VerificationService.empty_results()
        results['is_valid'] = is_valid
        VerificationService._extract_render_method(vc, results)
        return results['html_template']

    def test_the_first_template_is_taken(self):
        vc = {'renderMethod': [{'template': 'first'}, {'template': 'second'}]}
        self.assertEqual(self.extract(vc), 'first')

    def test_an_invalid_credential_keeps_its_template_out(self):
        # Rendering the template of a credential that failed its schema would
        # paint unvalidated markup.
        vc = {'renderMethod': [{'template': 'first'}]}
        self.assertIsNone(self.extract(vc, is_valid=False))

    def test_a_credential_without_a_render_method_has_no_template(self):
        for vc in ({}, {'renderMethod': []}, {'renderMethod': {'template': 'x'}}):
            with self.subTest(vc=vc):
                self.assertIsNone(self.extract(vc))


class VerifyDocumentTest(PatchMixin, SimpleTestCase):
    """The whole report, end to end."""

    def setUp(self):
        self.verify_signature = self.patch(
            'idhub.services.verify_signature', return_value=(True, 'ok')
        )
        self.verify_schema = self.patch(
            'idhub.services.verify_schema', return_value=(True, 'ok')
        )
        self.patch('idhub.services.VerificationService.validate_safe_host')

    CREDENTIAL = {
        '@context': ['https://www.w3.org/ns/credentials/v2'],
        'type': ['VerifiableCredential', 'DigitalProductPassport'],
        'issuer': {'id': 'https://issuer.example.org', 'name': 'Acme'},
        'credentialSubject': {'id': 'did:web:product.example.org', 'name': 'Drill'},
        'renderMethod': [{'template': '<p>{{ name }}</p>'}],
        'proof': {'verificationMethod': 'did:web:issuer.example.org#key-1'},
    }

    def verify(self, raw=None, **overrides):
        document = dict(self.CREDENTIAL, **overrides)
        return VerificationService.verify_document(
            raw if raw is not None else json.dumps(document)
        )

    def test_a_file_that_is_not_a_credential_gets_a_single_failed_step(self):
        results = VerificationService.verify_document('not a credential')
        self.assertEqual(self.outcomes(results), [('Format parsing', 'Failed')])
        self.assertIs(results['is_valid'], False)
        self.assertIsNone(results['payload'])
        self.verify_signature.assert_not_called()

    def test_a_signed_credential_that_matches_its_schema_is_valid(self):
        results = self.verify()
        self.assertIs(results['is_valid'], True)
        self.assertEqual(self.outcomes(results), [
            ('Format parsing', 'Success'),
            ('Cryptographic Integrity', 'Success'),
            ('Schema Verification', 'Success'),
        ])
        self.assertEqual(results['payload'], self.CREDENTIAL['credentialSubject'])
        self.assertEqual(results['issuer_name'], 'Acme')
        self.assertEqual(results['issuer_url'], 'https://issuer.example.org')
        self.assertEqual(results['html_template'], '<p>{{ name }}</p>')

    def test_a_schema_that_does_not_match_leaves_the_credential_invalid(self):
        self.verify_schema.return_value = (False, 'missing required property')
        results = self.verify()
        self.assertIs(results['is_valid'], False)
        self.assertEqual(
            self.details(results)[-1],
            'Schema validation failed: missing required property',
        )
        # The payload is filled in regardless, so the portal can show what
        # the document claimed even when it does not validate.
        self.assertEqual(results['payload'], self.CREDENTIAL['credentialSubject'])
        self.assertIsNone(results['html_template'])

    def test_a_failed_signature_stops_before_the_schema_is_looked_at(self):
        self.verify_signature.return_value = (False, 'digest mismatch')
        results = self.verify()
        self.verify_schema.assert_not_called()
        self.assertIs(results['is_valid'], False)
        self.assertIsNone(results['issuer_name'])
        self.assertEqual(self.outcomes(results), [
            ('Format parsing', 'Success'),
            ('Cryptographic Integrity', 'Failed'),
        ])

    def test_the_untp_schema_is_injected_before_the_check(self):
        self.verify()
        checked = json.loads(self.verify_schema.call_args.args[0])
        self.assertEqual(
            checked['credentialSchema']['id'],
            '{}/dpp/DigitalProductPassport.json'.format(UNTP_SCHEMA),
        )

    def test_a_credential_that_declares_its_schema_keeps_it(self):
        own = {'type': 'JsonSchema', 'id': 'https://example.org/mine.json'}
        self.verify(credentialSchema=own)
        checked = json.loads(self.verify_schema.call_args.args[0])
        self.assertEqual(checked['credentialSchema'], own)


DID_CONTEXT = 'https://www.w3.org/ns/did/v1'


class SyncEndpointToDocumentTest(SimpleTestCase):
    """Writing the ProductPassport service entry into the did document.

    The service mutates the row in memory and leaves saving to the caller, so
    no database is needed here.
    """

    DID = 'did:web:testserver:product:abc123'

    def sync(self, document=None, endpoint=''):
        obj_did = DID(
            did=self.DID,
            type=DID.Types.WEB.value,
            didweb_document='' if document is None else json.dumps(document),
            service_endpoint=endpoint,
        )
        returned = DIDService.sync_endpoint_to_document(obj_did)
        return returned, json.loads(returned.didweb_document)

    def product_entry(self):
        return {
            'id': self.DID + '#product',
            'type': 'ProductPassport',
            'serviceEndpoint': 'https://shop.example.org/p/1',
        }

    def test_a_did_without_a_document_gets_a_minimal_one(self):
        _obj, doc = self.sync()
        self.assertEqual(doc, {'@context': [DID_CONTEXT], 'id': self.DID})

    def test_a_document_that_is_not_json_is_silently_replaced(self):
        obj_did = DID(did=self.DID, didweb_document='<html>not json</html>')
        DIDService.sync_endpoint_to_document(obj_did)
        self.assertEqual(
            json.loads(obj_did.didweb_document),
            {'@context': [DID_CONTEXT], 'id': self.DID},
        )

    def test_the_endpoint_becomes_a_product_passport_service(self):
        _obj, doc = self.sync(endpoint='https://shop.example.org/p/1')
        self.assertEqual(doc['service'], [self.product_entry()])

    def test_a_previous_product_passport_entry_is_replaced(self):
        stale = dict(self.product_entry(), serviceEndpoint='https://old.example.org')
        _obj, doc = self.sync(
            document={'id': self.DID, 'service': [stale]},
            endpoint='https://shop.example.org/p/1',
        )
        self.assertEqual(doc['service'], [self.product_entry()])

    def test_services_of_another_type_are_kept(self):
        revocation = {
            'id': self.DID + '#revocation',
            'type': 'RevocationBitmap2022',
            'serviceEndpoint': 'https://testserver/revocation',
        }
        _obj, doc = self.sync(
            document={'id': self.DID, 'service': [revocation]},
            endpoint='https://shop.example.org/p/1',
        )
        self.assertEqual(doc['service'], [revocation, self.product_entry()])

    def test_dropping_the_endpoint_drops_the_whole_service_key(self):
        # An empty list would be valid JSON-LD, but the key is removed so the
        # document matches the one a did:web resolver would serve.
        _obj, doc = self.sync(
            document={'id': self.DID, 'service': [self.product_entry()]},
        )
        self.assertNotIn('service', doc)

    def test_dropping_the_endpoint_keeps_the_other_services(self):
        other = {'id': self.DID + '#other', 'type': 'LinkedDomains'}
        _obj, doc = self.sync(
            document={'id': self.DID, 'service': [other, self.product_entry()]},
        )
        self.assertEqual(doc['service'], [other])

    def test_the_rest_of_the_document_is_left_alone(self):
        document = {
            '@context': [DID_CONTEXT],
            'id': self.DID,
            'verificationMethod': [{'id': self.DID + '#owner'}],
            'authentication': [self.DID + '#owner'],
        }
        _obj, doc = self.sync(document=document, endpoint='https://shop.example.org/p/1')
        self.assertEqual(doc['verificationMethod'], document['verificationMethod'])
        self.assertEqual(doc['authentication'], document['authentication'])

    def test_the_same_row_is_returned_and_not_saved(self):
        obj_did = DID(did=self.DID, didweb_document='')
        self.assertIs(DIDService.sync_endpoint_to_document(obj_did), obj_did)
        self.assertIsNone(obj_did.pk)


class GetOrCreateProductDidTest(IdHubBaseTestCase):
    """The DID behind a product passport, created once and reused after that."""

    SUFFIX = 'abc123'
    ENDPOINT = 'https://shop.example.org/p/1'

    def setUp(self):
        super().setUp()
        self.user = make_user('owner@example.org', 'testpass12')

    def create(self, **overrides):
        kwargs = {
            'user': self.user,
            'did_type': DID.Types.WEB.value,
            'label': 'Drill 3000',
            'service_endpoint': self.ENDPOINT,
            'suffix_did_id': self.SUFFIX,
        }
        kwargs.update(overrides)
        return DIDService.get_or_create_product_did(**kwargs)

    def test_a_web_did_is_built_from_the_domain_and_the_suffix(self):
        obj_did, created = self.create()
        self.assertTrue(created)
        self.assertEqual(obj_did.did, 'did:web:testserver:' + self.SUFFIX)
        self.assertEqual(obj_did.label, 'Drill 3000')
        self.assertEqual(obj_did.user, self.user)
        self.assertTrue(obj_did.is_product)
        self.assertIsNotNone(obj_did.pk)

    def test_the_document_describes_the_final_did_not_the_generated_one(self):
        # set_did() builds a did of its own and a document to match; the
        # suffix then overwrites the did, so the document has to be rebuilt.
        obj_did, _created = self.create()
        document = json.loads(obj_did.didweb_document)
        self.assertEqual(document['id'], obj_did.did)
        self.assertEqual(
            document['verificationMethod'][0]['controller'], obj_did.did
        )

    def test_the_endpoint_is_published_as_a_service(self):
        obj_did, _created = self.create()
        services = json.loads(obj_did.didweb_document)['service']
        self.assertIn(
            {
                'id': obj_did.did + '#product',
                'type': 'ProductPassport',
                'serviceEndpoint': self.ENDPOINT,
            },
            services,
        )

    def test_a_second_call_with_the_same_suffix_reuses_the_row(self):
        first, _created = self.create()
        second, created = self.create(label='Another label')
        self.assertFalse(created)
        self.assertEqual(second.pk, first.pk)
        self.assertEqual(DID.objects.count(), 1)
        # The label of the existing row wins: only the endpoint is updated.
        self.assertEqual(second.label, 'Drill 3000')

    def test_a_different_endpoint_updates_the_row_and_the_document(self):
        self.create()
        moved = 'https://shop.example.org/p/moved'
        obj_did, _created = self.create(service_endpoint=moved)
        obj_did.refresh_from_db()
        self.assertEqual(obj_did.service_endpoint, moved)
        entries = [
            s for s in json.loads(obj_did.didweb_document)['service']
            if s['type'] == 'ProductPassport'
        ]
        self.assertEqual([s['serviceEndpoint'] for s in entries], [moved])

    def test_the_same_endpoint_leaves_the_row_untouched(self):
        self.create()
        with patch.object(DID, 'save') as save:
            self.create()
        save.assert_not_called()

    def test_an_empty_endpoint_does_not_wipe_the_stored_one(self):
        self.create()
        obj_did, _created = self.create(service_endpoint='')
        self.assertEqual(obj_did.service_endpoint, self.ENDPOINT)

    def test_a_did_that_is_not_a_product_is_not_reused(self):
        squatter = DID.objects.create(
            did='did:web:testserver:' + self.SUFFIX,
            type=DID.Types.WEB.value,
            label='Not a product',
            user=self.user,
        )
        obj_did, created = self.create()
        self.assertTrue(created)
        self.assertNotEqual(obj_did.pk, squatter.pk)
        # Two rows now answer to the same did; serve_did resolves whichever
        # comes first.
        self.assertEqual(DID.objects.filter(did=squatter.did).count(), 2)

    def test_a_key_did_keeps_the_did_it_generated(self):
        obj_did, created = self.create(did_type=DID.Types.KEY.value)
        self.assertTrue(created)
        self.assertTrue(obj_did.did.startswith('did:key:'))

    def test_a_key_did_ignores_the_suffix_and_is_never_reused(self):
        first, _created = self.create(did_type=DID.Types.KEY.value)
        second, created = self.create(did_type=DID.Types.KEY.value)
        self.assertTrue(created)
        self.assertNotEqual(second.did, first.did)
        self.assertEqual(DID.objects.count(), 2)

    def test_a_key_did_still_gets_a_document_for_its_endpoint(self):
        # gen_did_document() only answers for did:web, so the document of a
        # did:key is the minimal one sync_endpoint_to_document builds.
        obj_did, _created = self.create(did_type=DID.Types.KEY.value)
        self.assertEqual(json.loads(obj_did.didweb_document), {
            '@context': [DID_CONTEXT],
            'id': obj_did.did,
            'service': [{
                'id': obj_did.did + '#product',
                'type': 'ProductPassport',
                'serviceEndpoint': self.ENDPOINT,
            }],
        })

    def test_a_web_did_without_a_suffix_is_always_created(self):
        obj_did, created = self.create(suffix_did_id=None)
        self.assertTrue(created)
        self.assertTrue(obj_did.did.startswith('did:web:testserver'))
        self.assertNotEqual(obj_did.did, 'did:web:testserver:' + self.SUFFIX)
