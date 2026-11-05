"""Tests for the webhook app: the token pages, and the Token they manage.

Despite its name the app no longer serves any webhook: sign and verify moved
to the v1 API (idhub/api/api.py) and are tested in idhub/tests/test_api.py.
What is left matters more than before, though: Token is the authentication of
the whole API, so these pages are the only way to grant, restrict and revoke
machine access to it.
"""
from django.test import SimpleTestCase
from django.urls import reverse

from idhub.mixins import Http403
from idhub.models import DID
from test_support import factories
from test_support.base import IdHubTestCase
from webhook.models import Token


class WebhookTokenViewTest(IdHubTestCase):

    def setUp(self):
        super().setUp()
        self.admin_login()

    def test_render_tokens_page(self):
        response = self.client.get('/webhook/tokens/', follow=True)

        self.assertEqual(response.status_code, 200)

    def test_new_token(self):
        response = self.client.get('/webhook/tokens/new', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.count(), 0)

        response = self.client.post(
            '/webhook/tokens/new',
            data={"label": "Test token"},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.count(), 1)

        tk = Token.objects.first()
        self.assertEqual(tk.label, "Test token")
        self.assertTrue(tk.token)
        self.assertTrue(tk.active)
        url = "/webhook/tokens/{}/del".format(tk.id)
        response = self.client.get(url, follow=True)

        self.assertEqual(Token.objects.count(), 0)


class TokenAdminTestCase(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.token = Token.objects.create(label='Workbench', owner=self.admin_user)

    def url(self, name, *args):
        return reverse('webhook:{}'.format(name), args=args)


class TokenAdminTest(TokenAdminTestCase):
    """The token pages, and who can reach them."""

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

    def test_a_disabled_token_no_longer_opens_the_api(self):
        """Toggling is the only way to revoke access: the API reads the very
        same flag, so the effect is immediate."""
        bearer = {'HTTP_AUTHORIZATION': 'Bearer {}'.format(self.token.token)}
        api = '/api/v1/schemas/untp/active/'
        self.assertEqual(self.client.get(api, **bearer).status_code, 200)

        self.admin_login()
        self.client.get(self.url('status_token', self.token.id))

        self.assertEqual(self.client.get(api, **bearer).status_code, 401)

    def test_a_new_token_is_active_owned_by_its_creator_and_has_a_uuid_of_its_own(self):
        """The owner matters: DatabaseTokenAuth refuses a token without one."""
        self.admin_login()
        self.client.post(self.url('new_token'), data={'label': 'Second'})
        created = Token.objects.get(label='Second')

        self.assertTrue(created.active)
        self.assertEqual(created.owner, self.admin_user)
        self.assertNotEqual(created.token, self.token.token)

    def test_an_admin_deletes_a_token_with_a_get(self):
        """DeleteView, but acting on GET: no confirmation, no POST, no CSRF."""
        self.admin_login()
        response = self.client.get(self.url('delete_token', self.token.id))

        self.assertEqual(response['Location'], self.url('tokens'))
        self.assertFalse(Token.objects.exists())

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
        for name in ('tokens', 'new_token', 'status_token', 'delete_token',
                     'token_edit'):
            with self.subTest(url=name):
                args = [] if name in ('tokens', 'new_token') else [self.token.id]
                response = self.client.get(self.url(name, *args))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/login/?next='))


class TokenAllowedDidsTest(TokenAdminTestCase):
    """allowed_dids from the forms: which DIDs can be picked, and storing them.

    Whether the API then honours the restriction is another matter:
    AllowedDidsGuardTest in idhub/tests/test_api.py shows that it does not.
    """

    def setUp(self):
        super().setUp()
        self.issuer = factories.make_did(label='Issuer')
        self.other = factories.make_did(label='Other issuer')
        self.admin_login()

    def choices(self, response):
        field = response.context['form'].fields['allowed_dids']
        return set(field.queryset)

    def test_only_organization_dids_are_offered(self):
        factories.make_did(label='Wallet', user=self.user)
        DID.objects.create(label='Product', type=DID.Types.WEB.value,
                           did='did:web:testserver:product', is_product=True)

        for name, args in (('new_token', []), ('token_edit', [self.token.id])):
            with self.subTest(url=name):
                response = self.client.get(self.url(name, *args))
                self.assertEqual(self.choices(response), {self.issuer, self.other})

    def test_a_new_token_stores_the_dids_it_is_allowed(self):
        self.client.post(self.url('new_token'), data={
            'label': 'Restricted', 'allowed_dids': [self.issuer.id],
        })

        created = Token.objects.get(label='Restricted')
        self.assertEqual(list(created.allowed_dids.all()), [self.issuer])

    def test_a_did_that_is_not_offered_cannot_be_posted(self):
        wallet = factories.make_did(label='Wallet', user=self.user)

        response = self.client.post(self.url('new_token'), data={
            'label': 'Sneaky', 'allowed_dids': [wallet.id],
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('allowed_dids', response.context['form'].errors)
        self.assertFalse(Token.objects.filter(label='Sneaky').exists())


class TokenUpdateViewTest(TokenAdminTestCase):
    """The edit page: label, status and allowed DIDs of an existing token."""

    def setUp(self):
        super().setUp()
        self.issuer = factories.make_did(label='Issuer')
        self.admin_login()

    def edit(self, **data):
        payload = {'label': self.token.label, 'active': '1'}
        payload.update(data)
        return self.client.post(self.url('token_edit', self.token.id), data=payload)

    def test_the_page_shows_the_current_status(self):
        for active, expected in ((True, '1'), (False, '0')):
            with self.subTest(active=active):
                self.token.active = active
                self.token.save()
                response = self.client.get(self.url('token_edit', self.token.id))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['form'].initial['active'], expected)

    def test_the_label_is_changed_and_the_list_is_shown_again(self):
        response = self.edit(label='Renamed')

        self.assertEqual(response['Location'], self.url('tokens'))
        self.token.refresh_from_db()
        self.assertEqual(self.token.label, 'Renamed')

    def test_the_token_can_be_disabled_and_enabled_from_the_form(self):
        for value, expected in (('0', False), ('1', True)):
            with self.subTest(active=value):
                self.edit(active=value)
                self.token.refresh_from_db()
                self.assertEqual(self.token.active, expected)

    def test_a_status_that_is_not_a_choice_is_refused(self):
        response = self.edit(active='yes')

        self.assertEqual(response.status_code, 200)
        self.assertIn('active', response.context['form'].errors)
        self.token.refresh_from_db()
        self.assertTrue(self.token.active)

    def test_the_allowed_dids_are_replaced(self):
        other = factories.make_did(label='Other issuer')
        self.token.allowed_dids.add(other)

        self.edit(allowed_dids=[self.issuer.id])

        self.assertEqual(list(self.token.allowed_dids.all()), [self.issuer])

    def test_posting_no_dids_clears_them(self):
        self.token.allowed_dids.add(self.issuer)

        self.edit()

        self.assertFalse(self.token.allowed_dids.exists())

    def test_editing_neither_changes_the_secret_nor_the_owner(self):
        before = (self.token.token, self.token.owner)

        self.edit(label='Renamed')

        self.token.refresh_from_db()
        self.assertEqual((self.token.token, self.token.owner), before)

    def test_a_plain_user_is_bounced(self):
        self.client.logout()
        self.user_login()

        for method in ('get', 'post'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.url('token_edit', self.token.id),
                    **({'data': {'label': 'Hijacked', 'active': '0'}}
                       if method == 'post' else {}),
                )
                self.assertEqual(response['Location'], reverse('idhub:user_dashboard'))

        self.token.refresh_from_db()
        self.assertEqual(self.token.label, 'Workbench')
        self.assertTrue(self.token.active)


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
