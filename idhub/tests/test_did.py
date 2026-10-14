"""The DID model in isolation.

The network is reached from two places here: the DLT when minting a
Web+Ether DID, and ``check_remote_did``. Both are patched at
``idhub.models.requests`` so what is being asserted is the request this code
makes, not what a server answers.
"""
import json

from unittest.mock import Mock, patch

from django.test import override_settings
from django.urls import reverse

from idhub.models import DID
from oidc4vp.models import Organization
from test_support.base import IdHubTestCase


DLT_RESPONSES = {
    '/registerUser': {
        'data': {'api_token': 't' * 80, 'eth_pub_key': 'e' * 42},
    },
    '/getTa': {'data': {'root_pub_key': 'root-pub-key'}},
    '/getChainId': {'data': {'chain_id': 1337}},
}


def dlt_response(url, *args, **kwargs):
    for suffix, payload in DLT_RESPONSES.items():
        if url.endswith(suffix):
            return Mock(json=Mock(return_value=payload))
    raise AssertionError("unexpected DLT call: {}".format(url))


def http_response(status_code, text=''):
    return Mock(status_code=status_code, text=text)


class DidTypeTest(IdHubTestCase):
    def test_type_properties(self):
        expected = {
            DID.Types.KEY: False,
            DID.Types.WEB: True,
            DID.Types.WEBETH: True,
        }
        for type, is_web in expected.items():
            with self.subTest(type=type.label):
                did = DID(label='x', type=type.value)
                self.assertEqual(did.get_type(), type)
                self.assertEqual(did.is_web, is_web)
                self.assertEqual(did.has_link(), is_web)

    def test_is_organization_did_when_there_is_no_user(self):
        self.assertTrue(DID(label='x', type=DID.Types.KEY).is_organization_did)
        self.assertFalse(
            DID(label='x', type=DID.Types.KEY, user=self.user).is_organization_did
        )

    def test_get_organization_is_the_main_one(self):
        did = DID(label='x', type=DID.Types.KEY)
        self.assertEqual(did.get_organization(), self.org)
        self.assertTrue(self.org.main)


class DidKeyTest(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.did = DID(label='k', type=DID.Types.KEY, user=self.user)
        self.did.set_did()
        self.did.save()

    def test_set_did_builds_a_did_key(self):
        self.assertTrue(self.did.did.startswith('did:key:z6Mk'))
        # A did:key carries its own key, so there is no document to serve.
        self.assertEqual(self.did.didweb_document, '')

    def test_key_material_is_encrypted_at_rest(self):
        material = json.loads(self.did.get_key_material())
        self.assertEqual(material['crv'], 'Ed25519')
        self.assertIn('d', material)
        self.assertNotIn('Ed25519', self.did.key_material)

    def test_key_material_needs_the_key_in_cache(self):
        self.set_key_dids(None)
        with self.assertRaises(AttributeError):
            self.did.get_key_material()

    def test_get_key_cannot_read_the_stored_field(self):
        # get_key() parses key_material directly instead of going through
        # get_key_material(), so it chokes on the ciphertext. It has no
        # caller in production, which is why nobody noticed.
        with self.assertRaises(json.JSONDecodeError):
            self.did.get_key()

    def test_set_key_material_initialises_the_organization(self):
        org = Organization.objects.create(name='Second', main=False)
        self.assertFalse(org.encrypted_sensitive_data)

        did = DID(label='o', type=DID.Types.KEY)
        with patch.object(DID, 'get_organization', return_value=org):
            did.set_did()
            self.assertEqual(
                json.loads(did.get_key_material())['crv'], 'Ed25519'
            )
        self.assertTrue(Organization.objects.get(pk=org.pk).encrypted_sensitive_data)


class DidWebTest(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.did = DID(label='w', type=DID.Types.WEB, user=self.user)
        self.did.set_did()
        self.did.save()

    def test_set_did_builds_a_did_web_on_our_domain(self):
        prefix, method, domain, identifier = self.did.did.split(':')
        self.assertEqual((prefix, method), ('did', 'web'))
        self.assertEqual(domain, 'testserver')
        self.assertEqual(len(identifier), 6)

    def test_set_did_never_takes_the_path_branch(self):
        # set_did() only rewrites the base url when serve_did is not under
        # .well-known, and it always is, so the DID gets no path segment.
        self.assertIn('.well-known', reverse('idhub:serve_did', args=['a']))
        self.assertEqual(len(self.did.did.split(':')), 4)

    def test_set_did_fills_the_did_document(self):
        document = json.loads(self.did.didweb_document)
        self.assertIn('https://www.w3.org/ns/did/v1', document['@context'])
        self.assertEqual(document['id'], self.did.did)

    def test_get_did_document_mutates_instead_of_returning(self):
        self.did.didweb_document = ''
        self.assertIsNone(self.did.get_did_document())
        self.assertEqual(json.loads(self.did.didweb_document)['id'], self.did.did)

    def test_get_path_for_our_own_domain(self):
        identifier = self.did.did.split(':')[-1]
        self.assertEqual(
            self.did.get_path(), reverse('idhub:serve_did', args=[identifier])
        )

    def test_get_path_for_a_foreign_domain(self):
        expected = {
            'did:web:example.org:abc':
                'https://example.org/.well-known/abc/did.json',
            'did:web:example.org:a:b': 'https://example.org/a/b/did.json',
            # No path segment: the W3C default is /.well-known/did.json, but
            # this lands on the join branch instead. Unreachable from the
            # form, which rejects path-less did:web.
            'did:web:example.org': 'https://example.org/did.json',
        }
        for raw, path in expected.items():
            with self.subTest(did=raw):
                did = DID(label='x', type=DID.Types.WEB, did=raw)
                self.assertEqual(did.get_path(), path)

    def test_get_path_on_a_did_key_is_meaningless(self):
        # 'did:key:' and 'did:web:' are both 8 characters, so the did:web
        # branch happily builds a url out of the multibase key.
        did = DID(label='k', type=DID.Types.KEY, did='did:key:z6MkAbc')
        self.assertEqual(did.get_path(), 'https://z6MkAbc/did.json')


@override_settings(API_DLT_URL='http://dlt.example.org')
class DidWebEthTest(IdHubTestCase):
    def make_did(self):
        did = DID(label='e', type=DID.Types.WEBETH, user=self.user)
        with patch('idhub.models.requests.post', side_effect=dlt_response), \
             patch('idhub.models.requests.get', side_effect=dlt_response):
            did.set_did()
        did.save()
        return did

    def test_set_did_adds_the_ether_keys_to_the_key_material(self):
        material = json.loads(self.make_did().get_key_material())
        self.assertEqual(material['eth_api_token'], 't' * 80)
        self.assertEqual(material['eth_subject_pub_key'], 'e' * 42)
        self.assertEqual(material['eth_issuer_pub_key'], 'root-pub-key')
        self.assertEqual(material['eth_chainid'], 1337)
        self.assertEqual(material['crv'], 'Ed25519')

    def test_set_did_still_builds_a_did_web(self):
        self.assertTrue(self.make_did().did.startswith('did:web:testserver:'))

    def test_set_did_rejects_ether_keys_of_the_wrong_length(self):
        broken = {'data': {'api_token': 'short', 'eth_pub_key': 'e' * 42}}
        did = DID(label='e', type=DID.Types.WEBETH, user=self.user)

        with patch('idhub.models.requests.post',
                   return_value=Mock(json=Mock(return_value=broken))):
            with self.assertRaises(AssertionError):
                did.set_did()


class CheckRemoteDidTest(IdHubTestCase):
    DOCUMENT = '{"id": "did:web:example.org:abc"}'

    def make_did(self, type=DID.Types.WEB, did='did:web:example.org:abc'):
        return DID(
            label='x', type=type, did=did, didweb_document=self.DOCUMENT
        )

    def test_non_web_dids_are_never_checked(self):
        for type in (DID.Types.KEY, DID.Types.WEBETH):
            with self.subTest(type=type.label):
                with patch('idhub.models.requests.get') as get:
                    self.assertTrue(self.make_did(type=type).check_remote_did())
                get.assert_not_called()

    def test_matching_document(self):
        with patch('idhub.models.requests.get',
                   return_value=http_response(200, self.DOCUMENT)) as get:
            self.assertTrue(self.make_did().check_remote_did())

        get.assert_called_once_with(
            'https://example.org/.well-known/abc/did.json', verify=True
        )

    def test_a_different_document_is_rejected(self):
        with patch('idhub.models.requests.get',
                   return_value=http_response(200, '{"id": "someone else"}')):
            self.assertFalse(self.make_did().check_remote_did())

    def test_an_error_status_is_rejected(self):
        for status in (404, 500):
            with self.subTest(status=status):
                with patch('idhub.models.requests.get',
                           return_value=http_response(status, self.DOCUMENT)):
                    self.assertFalse(self.make_did().check_remote_did())

    def test_a_broken_request_is_rejected(self):
        with patch('idhub.models.requests.get', side_effect=OSError('down')):
            self.assertFalse(self.make_did().check_remote_did())

    def test_falls_back_to_plain_http(self):
        responses = [OSError('no tls'), http_response(200, self.DOCUMENT)]
        with patch('idhub.models.requests.get', side_effect=responses) as get:
            self.assertTrue(self.make_did().check_remote_did())

        self.assertEqual(
            [call.args[0] for call in get.call_args_list],
            ['https://example.org/.well-known/abc/did.json',
             'http://example.org/.well-known/abc/did.json'],
        )

    def test_tls_verification_follows_debug(self):
        for debug, verify in ((False, True), (True, False)):
            with self.subTest(debug=debug):
                with override_settings(DEBUG=debug):
                    with patch('idhub.models.requests.get',
                               return_value=http_response(200)) as get:
                        self.make_did().check_remote_did()
                self.assertEqual(get.call_args.kwargs['verify'], verify)

    def test_a_multi_segment_did_uses_the_plain_path(self):
        did = self.make_did(did='did:web:example.org:a:b')
        with patch('idhub.models.requests.get',
                   return_value=http_response(200, self.DOCUMENT)) as get:
            self.assertTrue(did.check_remote_did())

        self.assertEqual(get.call_args.args[0], 'https://example.org/a/b/did.json')
