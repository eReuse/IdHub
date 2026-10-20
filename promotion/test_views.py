"""The promotion flow: pick a wallet, come back with a code, get a discount.

This app is the Verifier side of a demo built for Som Connexió: a landing
page, a wallet chooser that sends the browser to the holder's IdHub, and a
contract form that comes back with a ``code`` and prices with 25 % off. The
views are not authenticated, so everything here is reachable by anybody with
the url.
"""
import json

from django.template.loader import get_template
from django.test import override_settings
from django.urls import reverse

from oidc4vp.models import Authorization, OAuth2VPToken, Organization
from promotion.models import Promotion
from test_support.base import IdHubBaseTestCase


SUPPORTED = ['MembershipCard']

VP_TOKEN = json.dumps({'verifiableCredential': [{'credentialSubject': {
    'identityNumber': '12345678Z',
    'firstName': 'Ana',
    'lastName': 'Pérez',
    'email': 'ana@example.org',
    'telephone': '600000000',
}}]})


def make_peer_organization(**kwargs):
    """A federated host: the wallet chooser only lists the ones that are not us."""
    defaults = {
        'name': 'Peer',
        'domain': 'peer.example.org',
        'response_uri': 'https://peer.example.org/oidc4vp/',
        'my_client_id': 'my-client-id',
        'my_client_secret': 'my-client-secret',
    }
    defaults.update(kwargs)
    return Organization.objects.create(**defaults)


class PromotionPageTest(IdHubBaseTestCase):
    """``/promotion/`` and ``/promotion/contract/1``: two static pages."""

    def test_the_landing_page_is_served_to_anybody(self):
        response = self.client.get(reverse('promotion:show_promotion'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response.headers['Content-Type'])

    def test_the_thanks_page_is_served_to_anybody(self):
        response = self.client.get(reverse('promotion:thanks'))

        self.assertEqual(response.status_code, 200)

    def test_neither_page_is_rendered_with_a_request(self):
        # Both views call get_template().render() with no context at all, so
        # nothing that needs the request works inside them: no csrf token, no
        # user, and the self.context they assign is never passed on.
        response = self.client.get(reverse('promotion:show_promotion'))

        self.assertEqual(
            response.content.decode(),
            get_template('somconnexio_tarifes_mobil.html').render(),
        )


@override_settings(SUPPORTED_CREDENTIALS=SUPPORTED)
class SelectWalletViewTest(IdHubBaseTestCase):
    """``/promotion/select_wallet``: where the browser is sent to the holder."""

    def setUp(self):
        super().setUp()
        self.url = reverse('promotion:select_wallet')
        self.org = make_peer_organization()

    def definition(self, response):
        return response.context['form'].presentation_definition

    def test_without_a_query_string_the_form_asks_for_everything_supported(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.definition(response), json.dumps(SUPPORTED))

    def test_a_presentation_definition_in_the_query_narrows_it_down(self):
        response = self.client.get(self.url, {
            'response_uri': 'https://verifier.example.org/oidc4vp',
            'presentation_definition': '["MembershipCard"]',
        })

        self.assertEqual(self.definition(response), '["MembershipCard"]')

    def test_the_response_uri_reaches_the_session_still_percent_encoded(self):
        # This is the only place that writes it, and oidc4vp's own views read
        # it back as a url to post the presentation to. But get_response_uri()
        # splits request.get_full_path() by hand instead of reading
        # request.GET, so nothing is unquoted: what gets stored is
        # https%3A%2F%2F... and whoever uses it has a broken url.
        self.client.get(self.url, {
            'response_uri': 'https://verifier.example.org/oidc4vp',
            'presentation_definition': '["MembershipCard"]',
        })

        self.assertEqual(
            self.client.session['response_uri'],
            'https%3A%2F%2Fverifier.example.org%2Foidc4vp',
        )

    def test_a_definition_nobody_supports_falls_back_to_the_whole_list(self):
        response = self.client.get(self.url, {
            'response_uri': 'https://verifier.example.org/oidc4vp',
            'presentation_definition': '["SomethingElse"]',
        })

        self.assertEqual(self.definition(response), json.dumps(SUPPORTED))

    def test_a_query_string_without_a_presentation_definition_is_a_500(self):
        # `for x in SUPPORTED_CREDENTIALS: if x in presentation` with
        # presentation None. Any link that carries only the response_uri
        # crashes instead of falling back to the supported list.
        with self.assertRaises(TypeError), self.assertLogs('django.request'):
            self.client.get(self.url, {'response_uri': 'https://v.example'})

    def test_a_raw_question_mark_in_the_query_swallows_the_rest(self):
        # The hand-rolled parser starts with get_full_path().split("?") and
        # keeps path[1], so everything after a second `?` is dropped: the
        # presentation_definition disappears and the None of the previous test
        # is what is left.
        with self.assertRaises(TypeError), self.assertLogs('django.request'):
            self.client.get(
                self.url + '?response_uri=https://v.example/?a=b'
                '&presentation_definition=["MembershipCard"]'
            )

    def test_a_value_carrying_an_equals_sign_is_a_500(self):
        # `dict([x.split("=") for x in ...])` needs exactly one `=` per
        # parameter, so any base64 value with its padding, or a nonce that
        # happens to contain one, takes the page down.
        with self.assertRaises(ValueError), self.assertLogs('django.request'):
            self.client.get(
                self.url + '?presentation_definition=["MembershipCard"]'
                '&state=YWJjZA=='
            )

    def test_only_the_organizations_that_are_not_us_can_be_picked(self):
        Organization.objects.create(name='Us', domain='testserver')

        choices = dict(self.client.get(self.url).context['form'].fields[
            'organization'
        ].choices)

        self.assertEqual(list(choices.values()), ['Peer'])

    def test_picking_a_wallet_redirects_to_its_authorize_url(self):
        response = self.client.post(self.url, {'organization': self.org.id})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response['Location'].startswith(
                'https://peer.example.org/oidc4vp/authorize?'
            ),
            response['Location'],
        )

    def test_picking_a_wallet_leaves_the_authorization_and_the_promotion(self):
        self.client.post(self.url, {'organization': self.org.id})

        authorization = Authorization.objects.get()
        self.assertEqual(authorization.organization, self.org)
        self.assertEqual(
            Promotion.objects.get().authorize_id, authorization.id
        )

    def test_the_code_of_the_new_authorization_travels_in_the_url(self):
        response = self.client.post(self.url, {'organization': self.org.id})

        self.assertIn(
            'code=' + Authorization.objects.get().code, response['Location']
        )

    def test_submitting_nothing_is_a_form_error_and_writes_no_rows(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(Authorization.objects.exists())


class ContractViewTest(IdHubBaseTestCase):
    """``/promotion/contract?code=...``: the form the discount is applied to."""

    FULL_PRICE = {'sim': 10.0, 'mensual': 15.0, 'total': 25.0}
    DISCOUNTED = {'sim': 7.5, 'mensual': 11.25, 'total': 18.75}

    def setUp(self):
        super().setUp()
        self.url = reverse('promotion:contract')
        self.org = make_peer_organization()

    def make_authorization(self, promotion=True, vp_token=None):
        authorization = Authorization.objects.create(
            organization=self.org, presentation_definition='["MembershipCard"]'
        )
        if promotion:
            Promotion.objects.create(
                name='Som Connexió',
                discount=Promotion.Types.VULNERABLE,
                authorize=authorization,
            )
        if vp_token is not None:
            OAuth2VPToken.objects.create(
                vp_token=vp_token,
                organization=self.org,
                code=authorization.code,
            )
        return authorization

    def prices(self, response):
        return {k: response.context[k] for k in self.FULL_PRICE}

    def test_without_a_code_the_prices_are_the_full_ones(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.prices(response), self.FULL_PRICE)
        self.assertIsNone(response.context['promotion'])

    def test_a_code_with_a_promotion_takes_a_quarter_off_the_three_prices(self):
        authorization = self.make_authorization()

        response = self.client.get(self.url, {'code': authorization.code})

        self.assertEqual(self.prices(response), self.DISCOUNTED)

    def test_a_code_nobody_issued_is_ignored_and_not_an_error(self):
        response = self.client.get(self.url, {'code': 'made-up-code'})

        self.assertEqual(self.prices(response), self.FULL_PRICE)

    def test_an_authorization_without_a_promotion_pays_the_full_price(self):
        authorization = self.make_authorization(promotion=False)

        response = self.client.get(self.url, {'code': authorization.code})

        self.assertEqual(self.prices(response), self.FULL_PRICE)

    def test_a_code_already_marked_as_used_gets_no_discount(self):
        # The filter asks for code_used=False, and nothing in the codebase ever
        # sets it to True (see §4): the guard works, but it never fires, so a
        # promotion code can be spent as many times as it is clicked.
        authorization = self.make_authorization()
        authorization.code_used = True
        authorization.save()

        response = self.client.get(self.url, {'code': authorization.code})

        self.assertEqual(self.prices(response), self.FULL_PRICE)

    def test_the_presentation_prefills_the_contract(self):
        authorization = self.make_authorization(vp_token=VP_TOKEN)

        response = self.client.get(self.url, {'code': authorization.code})

        initial = response.context['form'].initial
        self.assertEqual(initial['nif'], '12345678Z')
        self.assertEqual(initial['name'], 'Ana')
        self.assertEqual(initial['first_last_name'], 'Pérez')
        self.assertEqual(initial['email'], 'ana@example.org')
        self.assertEqual(initial['email_repeat'], 'ana@example.org')

    def test_the_fields_the_credential_does_not_carry_are_left_empty(self):
        authorization = self.make_authorization(vp_token=VP_TOKEN)

        initial = self.client.get(
            self.url, {'code': authorization.code}
        ).context['form'].initial

        self.assertEqual(initial['second_last_name'], '')
        self.assertEqual(initial['birthday'], '')

    def test_a_presentation_without_a_credential_subject_is_a_500(self):
        # get_user_info() leaves user_info as None and get_form_kwargs() calls
        # .get() on it straight away. A wallet that answers with a credential
        # shaped differently takes the page down.
        authorization = self.make_authorization(
            vp_token='{"verifiableCredential": [{}]}'
        )

        with self.assertRaises(AttributeError), self.assertLogs('django.request'):
            self.client.get(self.url, {'code': authorization.code})

    def test_the_filled_in_contract_is_a_redirect_to_the_thanks_page(self):
        response = self.client.post(self.url, {
            'nif': '12345678Z',
            'name': 'Ana',
            'first_last_name': 'Pérez',
            'second_last_name': 'García',
            'email': 'ana@example.org',
            'email_repeat': 'ana@example.org',
            'telephone': '600000000',
            'birthday': '1980-01-01',
            'gen': 'female',
            'lang': 'ca',
        })

        self.assertRedirects(
            response, reverse('promotion:thanks'), fetch_redirect_response=False,
        )

    def test_nothing_of_the_contract_is_stored_anywhere(self):
        # ContractForm is a plain Form and form_valid() only calls super(): the
        # demo collects a name, a nif, an address and a phone number and throws
        # them away. Whatever consumes this has to be outside the codebase.
        self.client.post(self.url, {
            'nif': '12345678Z', 'name': 'Ana', 'first_last_name': 'Pérez',
            'second_last_name': 'García', 'email': 'ana@example.org',
            'email_repeat': 'ana@example.org', 'telephone': '600000000',
            'birthday': '1980-01-01', 'gen': 'female', 'lang': 'ca',
        })

        self.assertFalse(Authorization.objects.exists())
        self.assertFalse(OAuth2VPToken.objects.exists())

    def test_an_incomplete_contract_comes_back_with_the_full_price(self):
        # The discount lives in the query string and the template posts to the
        # plain url, so a validation error loses the code: the same person is
        # shown 25 € after being shown 18,75 €.
        authorization = self.make_authorization()

        response = self.client.post(self.url, {'nif': '12345678Z'})

        self.assertTrue(response.context['form'].errors)
        self.assertEqual(self.prices(response), self.FULL_PRICE)
        self.assertTrue(Authorization.objects.filter(id=authorization.id).exists())
