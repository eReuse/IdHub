"""The two outbound calls an Organization makes to another instance.

``send`` posts a verifiable presentation to the Verifier and
``demand_authorization`` asks it to start a verification. Both are thin
wrappers over ``requests``, so what is worth pinning is the request they
build and what they hand back to the caller, not what a server replies.

``oidc4vp.models.requests`` is patched directly instead of going through
``OfflineHttpMixin``: these are the only two places in the project that call
out to a peer instance, and the url they build is the contract.
"""
from unittest.mock import patch

import requests

from django.test import SimpleTestCase

from oidc4vp.models import Organization


class OrganizationRequestTest(SimpleTestCase):
    def setUp(self):
        self.org = Organization(
            name='Verifier',
            response_uri='https://verifier.example.org/oidc4vp/',
            client_id='their-id-for-us',
            client_secret='their-secret-for-us',
            my_client_id='my-client-id',
            my_client_secret='my-client-secret',
        )
        patcher = patch('oidc4vp.models.requests')
        self.requests = patcher.start()
        self.addCleanup(patcher.stop)

    def test_send_posts_to_the_verify_endpoint(self):
        self.org.send('<the vp>', 'the-code')

        url, = self.requests.post.call_args.args
        self.assertEqual(url, 'https://verifier.example.org/oidc4vp/verify')

    def test_send_authenticates_with_the_credentials_we_were_given(self):
        self.org.send('<the vp>', 'the-code')

        self.assertEqual(
            self.requests.post.call_args.kwargs['auth'],
            ('my-client-id', 'my-client-secret'),
        )

    def test_send_puts_the_presentation_in_the_body(self):
        self.org.send('<the vp>', 'the-code')

        self.assertEqual(
            self.requests.post.call_args.kwargs['data'],
            {'vp_token': '<the vp>', 'code': 'the-code'},
        )

    def test_send_leaves_the_code_out_when_there_is_none(self):
        for code in (None, ''):
            with self.subTest(code=code):
                self.org.send('<the vp>', code)
                self.assertEqual(
                    self.requests.post.call_args.kwargs['data'],
                    {'vp_token': '<the vp>'},
                )

    def test_send_returns_the_response_untouched(self):
        self.assertIs(self.org.send('<the vp>', 'code'), self.requests.post())

    def test_send_does_not_swallow_a_transport_error(self):
        # AuthorizeForm.save() does not catch it either; the error surfaces as
        # a 500 unless the view wraps the call, which DemandAuthorizationView
        # does and AuthorizeView does not.
        self.requests.post.side_effect = requests.exceptions.Timeout
        with self.assertRaises(requests.exceptions.Timeout):
            self.org.send('<the vp>', 'code')

    def test_demand_authorization_asks_the_verify_endpoint_to_start(self):
        self.org.demand_authorization()

        url, = self.requests.get.call_args.args
        self.assertEqual(
            url,
            'https://verifier.example.org/oidc4vp/verify'
            '?demand_uri=https://verifier.example.org/oidc4vp/',
        )

    def test_the_demand_uri_keeps_the_slash_the_endpoint_loses(self):
        # The path is stripped for the endpoint and left alone for the
        # parameter, so the peer is told a slightly different url than the one
        # it was reached through. It is also sent unescaped.
        self.org.demand_authorization()

        url, = self.requests.get.call_args.args
        self.assertTrue(url.endswith('/oidc4vp/'), url)
        self.assertNotIn('%2F', url)

    def test_demand_authorization_authenticates_and_sends_no_body(self):
        self.org.demand_authorization()

        self.assertEqual(
            self.requests.get.call_args.kwargs,
            {'auth': ('my-client-id', 'my-client-secret')},
        )

    def test_demand_authorization_returns_the_response_untouched(self):
        self.assertIs(self.org.demand_authorization(), self.requests.get())

    def test_demand_authorization_does_not_swallow_a_transport_error(self):
        self.requests.get.side_effect = requests.exceptions.ConnectionError
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.org.demand_authorization()
