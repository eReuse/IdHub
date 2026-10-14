"""The redirection a Verifier sends the holder to.

``Authorization`` is the Verifier side of the handshake: it keeps the code
that ties a request to the response that comes back later, and builds the
``/authorize`` url the browser is sent to. Nothing here touches the network,
so the whole module runs without a database on unsaved rows.
"""
from urllib.parse import parse_qs, urlsplit

from django.test import SimpleTestCase

from oidc4vp.models import Authorization, Organization


PRESENTATION = '["Membership Card", "Course Credential"]'


def make_organization(response_uri='https://verifier.example.org/oidc4vp/'):
    return Organization(
        name='Verifier',
        response_uri=response_uri,
        my_client_id='my-client-id',
        my_client_secret='my-client-secret',
    )


class AuthorizeUrlTest(SimpleTestCase):
    def setUp(self):
        self.org = make_organization()
        self.authorization = Authorization(
            organization=self.org, presentation_definition=PRESENTATION
        )

    def params(self, **kwargs):
        return parse_qs(urlsplit(self.authorization.authorize(**kwargs)).query)

    def base_url(self, **kwargs):
        """The url without the query string, whose nonce changes every call."""
        return self.authorization.authorize(**kwargs).split('?')[0]

    def test_the_url_hangs_off_the_response_uri(self):
        url = self.authorization.authorize()

        self.assertTrue(
            url.startswith('https://verifier.example.org/oidc4vp/authorize?'),
            url,
        )

    def test_the_trailing_slash_of_the_response_uri_is_not_doubled(self):
        for response_uri in (
            'https://verifier.example.org/oidc4vp',
            'https://verifier.example.org/oidc4vp/',
        ):
            with self.subTest(response_uri=response_uri):
                self.authorization.organization = make_organization(response_uri)
                self.assertNotIn(
                    '//authorize', self.authorization.authorize()
                )

    def test_the_query_string_carries_the_oidc4vp_request(self):
        params = self.params()

        self.assertEqual(params['response_type'], ['vp_token'])
        self.assertEqual(params['response_mode'], ['direct_post'])
        self.assertEqual(params['client_id'], ['my-client-id'])
        self.assertEqual(params['code'], [self.authorization.code])

    def test_the_client_id_sent_is_the_one_we_use_to_call_them(self):
        # client_id/client_secret are how they reach us; my_* is how we reach
        # them, and the authorization request travels in that direction.
        self.org.client_id = 'their-id-for-us'
        self.assertEqual(self.params()['client_id'], ['my-client-id'])

    def test_the_presentation_definition_travels_escaped(self):
        self.assertEqual(self.params()['presentation_definition'], [PRESENTATION])

    def test_a_nonce_of_five_characters_is_added_on_every_call(self):
        first, second = self.params()['nonce'], self.params()['nonce']

        self.assertEqual(len(first[0]), 5)
        self.assertNotEqual(first, second)

    def test_a_path_is_inserted_before_authorize(self):
        url = self.authorization.authorize(path='somconnexio')

        self.assertTrue(
            url.startswith(
                'https://verifier.example.org/oidc4vp/somconnexio/authorize?'
            ),
            url,
        )

    def test_the_slashes_around_the_path_are_stripped(self):
        self.assertEqual(
            self.base_url(path='/somconnexio/'), self.base_url(path='somconnexio')
        )

    def test_an_empty_path_is_the_same_as_no_path(self):
        self.assertEqual(self.base_url(path=''), self.base_url())

    def test_without_an_organization_it_raises(self):
        # The field is nullable and nothing checks it: VerifyView always has
        # an organization because validate() refuses the request otherwise.
        with self.assertRaises(AttributeError):
            Authorization(presentation_definition=PRESENTATION).authorize()


class AuthorizationFieldsTest(SimpleTestCase):
    def test_the_code_is_generated_on_instantiation(self):
        authorization = Authorization(presentation_definition=PRESENTATION)

        self.assertEqual(len(authorization.code), 24)
        self.assertNotEqual(
            authorization.code,
            Authorization(presentation_definition=PRESENTATION).code,
        )

    def test_a_fresh_authorization_is_not_marked_as_used(self):
        self.assertFalse(Authorization(presentation_definition=PRESENTATION).code_used)
