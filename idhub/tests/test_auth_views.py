"""Login, the second factor and the password reset flow.

These four views override Django's own, and every override drops part of what
Django did: the ``next`` url stops being validated, the reset form stops
reporting failures and the confirmation stops going through ``super()``. The
tests pin what is left.
"""
from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.urls import NoReverseMatch, reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from idhub.views import LoginView
from test_support import factories
from test_support.base import IdHubTestCase


class LoginViewTest(IdHubTestCase):
    """``/login/``: the only unauthenticated page that writes to the session."""

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:login')

    def login(self, **extra):
        data = {'username': self.USER_EMAIL, 'password': self.USER_PASSWORD}
        data.update(extra)
        return self.client.post(self.url, data)

    def test_an_anonymous_visitor_gets_the_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_a_logged_in_user_is_sent_to_their_own_dashboard(self):
        self.user_login()

        self.assertRedirects(
            self.client.get(self.url), reverse('idhub:user_dashboard'),
            fetch_redirect_response=False,
        )

    def test_a_logged_in_admin_is_sent_to_the_admin_dashboard(self):
        self.admin_login()

        self.assertRedirects(
            self.client.get(self.url), reverse('idhub:admin_dashboard'),
            fetch_redirect_response=False,
        )

    def test_a_user_who_signs_in_lands_on_the_user_dashboard(self):
        response = self.login()

        self.assertRedirects(
            response, reverse('idhub:user_dashboard'),
            fetch_redirect_response=False,
        )

    def test_a_wrong_password_leaves_no_session(self):
        response = self.login(password='not the password')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(ENABLE_2FACTOR_AUTH=True)
    def test_an_admin_is_sent_to_the_second_factor_with_a_token_in_session(self):
        response = self.client.post(
            self.url,
            {'username': self.ADMIN_EMAIL, 'password': self.ADMIN_PASSWORD},
        )

        self.assertRedirects(
            response, reverse('idhub:confirm_send_2f'),
            fetch_redirect_response=False,
        )
        self.assertTrue(self.client.session['2fauth'])

    @override_settings(ENABLE_2FACTOR_AUTH=False)
    def test_with_the_second_factor_off_the_admin_goes_straight_in(self):
        response = self.client.post(
            self.url,
            {'username': self.ADMIN_EMAIL, 'password': self.ADMIN_PASSWORD},
        )

        self.assertRedirects(
            response, reverse('idhub:admin_dashboard'),
            fetch_redirect_response=False,
        )
        self.assertNotIn('2fauth', self.client.session)

    def test_the_next_url_is_followed_wherever_it_points(self):
        # Django's LoginView runs the value through
        # url_has_allowed_host_and_scheme(); this override does not, so the
        # login page of the deployment redirects to any host a link asks for.
        response = self.login(next='https://not-us.example/phishing')

        self.assertEqual(response['Location'], 'https://not-us.example/phishing')

    @override_settings(ENABLE_2FACTOR_AUTH=True)
    def test_the_next_url_also_skips_the_second_factor(self):
        # The `next` branch returns before the is_admin check, so an admin who
        # arrives with ?next=... is logged in without the email token.
        response = self.client.post(
            self.url,
            {
                'username': self.ADMIN_EMAIL,
                'password': self.ADMIN_PASSWORD,
                'next': reverse('idhub:admin_dashboard'),
            },
        )

        self.assertEqual(response['Location'], reverse('idhub:admin_dashboard'))
        self.assertNotIn('2fauth', self.client.session)
        self.assertEqual(
            self.client.session['_auth_user_id'], str(self.admin_user.id)
        )

    def test_the_organization_shown_is_the_one_that_existed_at_import_time(self):
        # LoginView queries Organization in the class body, so extra_context is
        # frozen when the module is imported: renaming the organization, or
        # creating it after the process started, is invisible until a restart.
        self.org.name = 'Renamed after the import'
        self.org.save()

        self.assertNotEqual(LoginView.extra_context['org'], self.org.name)


class PasswordResetTest(IdHubTestCase):
    """``/auth/password_reset/``: asking for the email with the link."""

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:password_reset')

    @override_settings(ENABLE_EMAIL=True)
    def test_a_known_address_gets_a_mail_with_a_usable_link(self):
        response = self.client.post(self.url, {'email': self.USER_EMAIL})

        self.assertRedirects(
            response, reverse('idhub:password_reset_done'),
            fetch_redirect_response=False,
        )
        message, = mail.outbox
        self.assertEqual(message.to, [self.USER_EMAIL])
        self.assertIn('/auth/reset/', message.body)

    @override_settings(ENABLE_EMAIL=True)
    def test_an_address_nobody_registered_answers_exactly_the_same(self):
        response = self.client.post(self.url, {'email': 'nobody@example.org'})

        self.assertRedirects(
            response, reverse('idhub:password_reset_done'),
            fetch_redirect_response=False,
        )
        self.assertEqual(mail.outbox, [])

    @override_settings(ENABLE_EMAIL=True)
    def test_an_inactive_account_is_not_written_to(self):
        self.user.is_active = False
        self.user.save()

        self.client.post(self.url, {'email': self.USER_EMAIL})

        self.assertEqual(mail.outbox, [])

    def test_a_mail_server_that_is_down_is_reported_as_a_success(self):
        # form_valid() catches every exception and returns success_url anyway.
        # Telling the user nothing is the right call for address enumeration,
        # but here it also hides a broken SMTP: the only trace is the log.
        with patch(
            'django.contrib.auth.forms.PasswordResetForm.save',
            side_effect=OSError('smtp is down'),
        ):
            with self.assertLogs('idhub.views', level='ERROR') as logs:
                response = self.client.post(self.url, {'email': self.USER_EMAIL})

        self.assertRedirects(
            response, reverse('idhub:password_reset_done'),
            fetch_redirect_response=False,
        )
        self.assertIn('smtp is down', logs.output[0])

    def test_an_address_that_is_not_an_address_is_a_form_error(self):
        response = self.client.post(self.url, {'email': 'not an email'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)


class PasswordResetConfirmTest(IdHubTestCase):
    """``/auth/reset/<uid>/<token>/``: typing the new password."""

    NEW_PASSWORD = 'a-brand-new-one-12'

    def url(self, user=None, token=None):
        user = user or self.user
        return reverse('idhub:password_reset_confirm', kwargs={
            'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': token or default_token_generator.make_token(user),
        })

    def post(self, url, password=None):
        # Django's view only accepts the form on the url it redirects to, with
        # the token moved into the session.
        password = password or self.NEW_PASSWORD
        self.client.get(url)
        return self.client.post(url.replace(url.split('/')[-2], 'set-password'), {
            'new_password1': password,
            'new_password2': password,
        })

    def test_the_new_password_replaces_the_old_one(self):
        response = self.post(self.url())

        self.assertRedirects(
            response, reverse('idhub:password_reset_complete'),
            fetch_redirect_response=False,
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.NEW_PASSWORD))
        self.assertFalse(self.user.check_password(self.USER_PASSWORD))

    def test_two_different_passwords_are_a_form_error(self):
        url = self.url()
        self.client.get(url)
        response = self.client.post(
            url.replace(url.split('/')[-2], 'set-password'),
            {'new_password1': self.NEW_PASSWORD, 'new_password2': 'something else'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.USER_PASSWORD))

    def test_a_token_that_was_never_issued_is_refused(self):
        response = self.client.get(self.url(token='made-up-token'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])

    def test_the_link_stops_working_once_the_password_changed(self):
        # The override does set_password() and saves, which is what rotates the
        # token: the hash of the old password is part of what signs it. So even
        # without calling super() the link is single use.
        url = self.url()
        self.post(url)

        self.assertFalse(self.client.get(url).context['validlink'])


class DobleFactorSendTest(IdHubTestCase):
    """``/admin/auth/2f/``: the page that emails the admin their token."""

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:confirm_send_2f')

    TOKEN = '3f2504e0-4f89-11d3-9a0c-0305e82c3301'

    def put_token_in_session(self, token=None):
        session = self.client.session
        session['2fauth'] = token or self.TOKEN
        session.save()

    def test_without_a_session_nothing_is_sent(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(mail.outbox, [])

    def test_a_normal_user_cannot_reach_the_admin_second_factor(self):
        self.user_login()
        self.put_token_in_session()

        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_an_admin_without_a_token_in_session_is_a_404(self):
        self.admin_login()

        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(mail.outbox, [])

    @override_settings(ENABLE_EMAIL=True)
    def test_the_mail_carries_the_token_the_session_holds(self):
        self.admin_login()
        self.put_token_in_session()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        message, = mail.outbox
        self.assertEqual(message.to, [self.ADMIN_EMAIL])
        self.assertIn(self.TOKEN, message.body)

    @override_settings(ENABLE_EMAIL=True)
    def test_a_session_token_that_is_not_a_uuid_crashes_the_mail(self):
        # The admin_2fauth route only matches a uuid, and the email template
        # reverses it with whatever the session holds. LoginView does write a
        # uuid4, so this is not reachable today; it is pinned because it means
        # the session value is load-bearing for the template, not just for the
        # comparison that follows.
        self.admin_login()
        self.put_token_in_session('not-a-uuid')

        with self.assertRaises(NoReverseMatch), self.assertLogs('django.request'):
            self.client.get(self.url)
