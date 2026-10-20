from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, override_settings

from utils.sanitize_did import sanitize_didweb, sanitize_path, sanitize_url


OWN_DOMAIN = 'idhub.example.org'
OTHER_DOMAIN = 'other.example.com'


class SanitizeUrlTest(SimpleTestCase):

    def test_accepts_https_domain(self):
        self.assertTrue(sanitize_url('https://idhub.example.org'))

    def test_accepts_https_with_path(self):
        self.assertTrue(sanitize_url('https://idhub.example.org/did-registry'))
        self.assertTrue(sanitize_url('https://idhub.example.org/a/b/c'))

    def test_rejects_plain_http(self):
        self.assertFalse(sanitize_url('http://idhub.example.org'))

    def test_rejects_missing_scheme(self):
        self.assertFalse(sanitize_url('idhub.example.org'))
        self.assertFalse(sanitize_url('//idhub.example.org'))

    def test_rejects_domain_without_dot(self):
        self.assertFalse(sanitize_url('https://localhost'))

    def test_rejects_empty_string(self):
        self.assertFalse(sanitize_url(''))

    def test_rejects_whitespace_and_control_chars(self):
        self.assertFalse(sanitize_url('https://idhub.example.org/a b'))
        self.assertFalse(sanitize_url('https://idhub.example.org\n'))
        self.assertFalse(sanitize_url('https://idhub.example.org/a\x00'))

    def test_accepts_dot_in_path(self):
        # Required so that the /did.json suffix of a did:web validates.
        self.assertTrue(sanitize_url('https://idhub.example.org/a.json'))
        self.assertTrue(sanitize_url('https://idhub.example.org/a/did.json'))

    def test_still_rejects_dot_only_segments(self):
        self.assertFalse(sanitize_url('https://idhub.example.org/../a'))
        self.assertFalse(sanitize_url('https://idhub.example.org/./a'))
        self.assertFalse(sanitize_url('https://idhub.example.org/a/..'))

    def test_rejects_port(self):
        self.assertFalse(sanitize_url('https://idhub.example.org:3000'))

    def test_rejects_query_string(self):
        self.assertFalse(sanitize_url('https://idhub.example.org/a?b=1'))


class SanitizePathTest(SimpleTestCase):

    def test_accepts_segments(self):
        self.assertTrue(sanitize_path('/did-registry'))
        self.assertTrue(sanitize_path('/a/b/c'))
        self.assertTrue(sanitize_path('/a_b-c'))

    def test_accepts_empty_string(self):
        self.assertTrue(sanitize_path(''))

    def test_rejects_lone_slash(self):
        self.assertFalse(sanitize_path('/'))

    def test_rejects_double_slash(self):
        self.assertFalse(sanitize_path('//a'))
        self.assertFalse(sanitize_path('/a//b'))

    def test_rejects_traversal(self):
        self.assertFalse(sanitize_path('/..'))
        self.assertFalse(sanitize_path('/a/../b'))

    def test_accepts_dot_in_segment(self):
        self.assertTrue(sanitize_path('/a.json'))
        self.assertTrue(sanitize_path('/a/did.json'))

    def test_rejects_trailing_slash(self):
        self.assertFalse(sanitize_path('/a/'))


@override_settings(DOMAIN=OWN_DOMAIN)
class SanitizeDidWebTest(SimpleTestCase):

    def assertInvalid(self, did, message):
        with self.assertRaises(ValidationError) as ctx:
            sanitize_didweb(did)
        self.assertEqual(ctx.exception.messages, [message])

    def test_rejects_non_didweb_prefix(self):
        self.assertInvalid('did:key:z6Mk', "This is not a correct DID web")
        self.assertInvalid('http://idhub.example.org', "This is not a correct DID web")
        self.assertInvalid('', "This is not a correct DID web")

    def test_rejects_slash(self):
        self.assertInvalid(
            'did:web:{}/path'.format(OTHER_DOMAIN),
            "This is not a correct DID web",
        )

    def test_none_is_not_handled(self):
        # Edge contract: the caller must guarantee a string.
        with self.assertRaises(TypeError):
            sanitize_didweb(None)

    def test_accepts_own_domain_with_one_path_segment(self):
        did = 'did:web:{}:did-registry'.format(OWN_DOMAIN)
        self.assertEqual(sanitize_didweb(did), did)

    def test_own_domain_accepts_up_to_a_double_path_level(self):
        for did in (
            'did:web:{}'.format(OWN_DOMAIN),
            'did:web:{}:a'.format(OWN_DOMAIN),
            'did:web:{}:a:b'.format(OWN_DOMAIN),
        ):
            with self.subTest(did=did):
                self.assertEqual(sanitize_didweb(did), did)

    def test_own_domain_refuses_a_deeper_path(self):
        self.assertInvalid(
            'did:web:{}:a:b:c'.format(OWN_DOMAIN),
            "Only a double path level is permitted for this domain.",
        )

    def test_accepts_other_domain_with_path(self):
        did = 'did:web:{}:path'.format(OTHER_DOMAIN)
        self.assertEqual(sanitize_didweb(did), did)

    def test_accepts_other_domain_with_several_path_segments(self):
        did = 'did:web:{}:a:b'.format(OTHER_DOMAIN)
        self.assertEqual(sanitize_didweb(did), did)

    def test_accepts_any_domain_without_path(self):
        # A base level did:web resolves to /.well-known/did.json, per the spec.
        did = 'did:web:{}'.format(OTHER_DOMAIN)
        self.assertEqual(sanitize_didweb(did), did)

    def test_lowercases_the_domain_only(self):
        did = sanitize_didweb('did:web:OTHER.EXAMPLE.COM:PaTh')
        self.assertEqual(did, 'did:web:other.example.com:PaTh')

    def test_own_domain_comparison_is_case_insensitive(self):
        self.assertInvalid(
            'did:web:IDHUB.EXAMPLE.ORG:a:b:c',
            "Only a double path level is permitted for this domain.",
        )

    def test_rejects_traversal_in_path(self):
        self.assertInvalid(
            'did:web:{}:..:etc'.format(OTHER_DOMAIN),
            "Is not a valid url",
        )

    def test_rejects_encoded_port(self):
        self.assertInvalid(
            'did:web:{}%3A3000:path'.format(OTHER_DOMAIN),
            "Is not a valid url",
        )

    def test_rejects_whitespace(self):
        self.assertInvalid('did:web: {}:path'.format(OTHER_DOMAIN), "Is not a valid url")
        self.assertInvalid('did:web:{}:path\n'.format(OTHER_DOMAIN), "Is not a valid url")

    def test_rejects_empty_domain(self):
        self.assertInvalid('did:web::path', "Is not a valid url")
