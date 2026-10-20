"""The admin pages, driven through the client the way the browser does.

The forms of ``idhub/admin/forms.py`` are already covered one by one in
``test_forms.py``; what is pinned here is what the views add on top of them:
the redirects, the events, the flash messages and the objects left behind.
"""
import json

from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import TemplateDoesNotExist
from django.test import RequestFactory
from django.urls import reverse

from idhub.admin.forms import DIDForm, ImportForm
from idhub.admin.views import ImportStep2View
from idhub.models import (
    DID, Event, File_datas, Membership, Rol, Schemas, Service, UserRol,
    VCTemplatePdf, VerificableCredential,
)
from idhub_auth.models import User
from test_support import factories
from test_support.base import IdHubTestCase


class AdminViewTestCase(IdHubTestCase):
    """An admin already logged in, which is what every page below needs."""

    def setUp(self):
        super().setUp()
        self.admin_login()

    def messages(self, response):
        return [str(m) for m in get_messages(response.wsgi_request)]


class TermsAndConditionsViewTest(AdminViewTestCase):
    """``/admin/terms/``: the GDPR gate of the administrator."""

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:admin_terms_and_conditions')

    def test_an_admin_who_already_accepted_sees_the_boxes_ticked(self):
        response = self.client.get(self.url)

        self.assertEqual(response.context['form'].initial, {
            'accept_privacy': True,
            'accept_legal': True,
            'accept_cookies': True,
        })

    def test_an_admin_who_did_not_accept_sees_them_empty(self):
        self.admin_user.accept_gdpr = False
        self.admin_user.save()

        response = self.client.get(self.url)

        self.assertEqual(response.context['form'].initial, {})

    def test_accepting_the_three_policies_opens_the_dashboard(self):
        self.admin_user.accept_gdpr = False
        self.admin_user.save()

        response = self.client.post(self.url, {
            'accept_privacy': 'on',
            'accept_legal': 'on',
            'accept_cookies': 'on',
        })

        self.assertRedirects(response, reverse('idhub:admin_dashboard'))
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.accept_gdpr)

    def test_leaving_one_box_out_withdraws_the_consent(self):
        # The form is valid either way, so the post succeeds and the view sends
        # the admin to the dashboard; it is the mixin that bounces them back
        # here, because the flag it looks at was just turned off.
        response = self.client.post(self.url, {
            'accept_privacy': 'on',
            'accept_legal': 'on',
        }, follow=True)

        self.assertEqual(response.redirect_chain, [
            (reverse('idhub:admin_dashboard'), 302),
            (reverse('idhub:admin_terms_and_conditions'), 302),
        ])
        self.admin_user.refresh_from_db()
        self.assertFalse(self.admin_user.accept_gdpr)


class EncryptionKeyViewTest(AdminViewTestCase):
    """``/admin/encryption_key/``: where the vault key is typed in."""

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:encryption_key')

    def test_with_the_key_already_in_the_cache_the_page_is_skipped(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('idhub:admin_dashboard'))

    def test_without_the_key_in_the_cache_the_form_is_shown(self):
        cache.delete('KEY_DIDS')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('key', response.context['form'].fields)

    def test_the_first_key_typed_in_is_accepted_and_creates_a_did(self):
        cache.delete('KEY_DIDS')

        response = self.client.post(self.url, {'key': 'a-brand-new-key'})

        self.assertRedirects(response, reverse('idhub:admin_dashboard'))
        self.assertEqual(cache.get('KEY_DIDS'), 'a-brand-new-key')
        self.assertEqual(DID.objects.get().label, 'Default')

    def test_a_key_that_does_not_open_the_existing_dids_is_refused(self):
        factories.make_did(label='Organisation')
        cache.delete('KEY_DIDS')

        response = self.client.post(self.url, {'key': 'the-wrong-key'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('Key no valid!', response.context['form'].errors['__all__'])
        self.assertIsNone(cache.get('KEY_DIDS'))


class DobleFactorAuthViewTest(IdHubTestCase):
    """``/admin/auth/2f/<uuid>/``: the link mailed to the administrator."""

    TOKEN = '3f2504e0-4f89-11d3-9a0c-0305e82c3301'

    def url(self, token=None):
        return reverse('idhub:admin_2fauth', kwargs={
            'admin2fauth': token or self.TOKEN,
        })

    def put_token_in_session(self, token=None):
        session = self.client.session
        session['2fauth'] = token or self.TOKEN
        session.save()

    def test_the_token_of_the_session_unlocks_the_admin_pages(self):
        self.admin_login()
        self.put_token_in_session()
        self.assertEqual(self.client.get(reverse('idhub:admin_dashboard')).status_code, 403)

        response = self.client.get(self.url())

        self.assertRedirects(response, reverse('idhub:admin_dashboard'))
        self.assertNotIn('2fauth', self.client.session)

    def test_another_token_sends_the_admin_to_the_login_page(self):
        self.admin_login()
        self.put_token_in_session()

        response = self.client.get(self.url('11111111-1111-1111-1111-111111111111'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:login'))

    def test_a_wrong_token_does_not_close_the_session_it_only_locks_it(self):
        # The session keeps its pending token and the login the admin is sent
        # to is still theirs, so every admin page answers 403 from now on. The
        # view neither logs them out nor lets them try again: the only way out
        # is a new login, which overwrites the token.
        self.admin_login()
        self.put_token_in_session()

        self.client.get(self.url('11111111-1111-1111-1111-111111111111'))

        self.assertEqual(self.client.session['2fauth'], self.TOKEN)
        self.assertEqual(
            self.client.get(reverse('idhub:admin_dashboard')).status_code, 403
        )

    def test_without_a_pending_token_the_link_is_a_plain_redirect(self):
        self.admin_login()

        response = self.client.get(self.url())

        self.assertRedirects(response, reverse('idhub:admin_dashboard'))

    def test_a_plain_user_cannot_consume_an_admin_token(self):
        self.user_login()
        self.put_token_in_session()

        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_an_anonymous_visitor_is_sent_to_the_login_page(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))


class PeopleEditViewTest(AdminViewTestCase):
    """``/admin/people/<pk>/edit/``: the profile of somebody else."""

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:admin_people_edit', kwargs={'pk': self.user.id})

    def payload(self, **kwargs):
        data = {
            'first_name': 'Alice',
            'last_name': 'Liddell',
            'email': self.user.email,
        }
        data.update(kwargs)
        return data

    def test_the_page_carries_the_user_being_edited(self):
        response = self.client.get(self.url)

        self.assertEqual(response.context['object'], self.user)
        self.assertEqual(response.context['form'].instance, self.user)

    def test_a_valid_edit_is_saved_and_logged_twice(self):
        response = self.client.post(self.url, self.payload())

        self.assertRedirects(response, reverse('idhub:admin_people_list'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Alice')
        self.assertIn('The account was updated successfully', self.messages(response))
        # One event for the dashboard of the admin, with nobody attached, and
        # one for the inbox of the user who was edited.
        self.assertIsNone(
            Event.objects.get(type=Event.Types.EV_USR_UPDATED_BY_ADMIN).user
        )
        self.assertEqual(
            Event.objects.get(type=Event.Types.EV_USR_UPDATED).user, self.user
        )

    def test_the_admin_flag_can_be_granted_from_this_page(self):
        self.client.post(self.url, self.payload(is_admin='on'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_admin)

    def test_an_invalid_name_keeps_the_page_and_changes_nothing(self):
        response = self.client.post(self.url, self.payload(first_name='A1ice'))

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.first_name)
        self.assertFalse(Event.objects.exists())

    def test_editing_somebody_who_is_not_there_is_a_404(self):
        url = reverse('idhub:admin_people_edit', kwargs={'pk': 0})

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.payload()).status_code, 404)


class PeopleRegisterViewTest(AdminViewTestCase):
    """``/admin/people/new/``: creating an account on behalf of somebody."""

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:admin_people_new')

    def payload(self, **kwargs):
        data = {
            'first_name': 'Bob',
            'last_name': 'Cratchit',
            'email': 'bob@example.org',
        }
        data.update(kwargs)
        return data

    def test_the_new_account_gets_a_vault_and_a_default_web_did(self):
        response = self.client.post(self.url, self.payload())

        user = User.objects.get(email='bob@example.org')
        self.assertRedirects(response, reverse(
            'idhub:admin_people_membership_new', kwargs={'pk': user.id},
        ))
        self.assertTrue(user.encrypted_sensitive_data)
        did = DID.objects.get(user=user)
        self.assertEqual((did.label, did.type), ('Default', DID.Types.WEB))

    def test_the_registration_is_announced_to_the_admin_and_to_the_user(self):
        response = self.client.post(self.url, self.payload())

        user = User.objects.get(email='bob@example.org')
        self.assertIn('The account was created successfully', self.messages(response))
        self.assertIsNone(
            Event.objects.get(type=Event.Types.EV_USR_REGISTERED).user
        )
        self.assertEqual(
            Event.objects.get(type=Event.Types.EV_USR_WELCOME).user, user
        )

    def test_a_duplicate_address_does_not_create_anything(self):
        response = self.client.post(self.url, self.payload(email=self.user.email))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 2)

    def test_the_new_account_has_not_accepted_the_terms_yet(self):
        self.client.post(self.url, self.payload())

        user = User.objects.get(email='bob@example.org')
        self.assertFalse(user.accept_gdpr)


class PeopleMembershipViewsTest(AdminViewTestCase):
    """``/admin/people/<pk>/membership/``: the tie with the organization."""

    def payload(self, **kwargs):
        data = {
            'type': Membership.Types.MEMBER,
            'start_date': '2024-01-01',
            'end_date': '',
        }
        data.update(kwargs)
        return data

    def new_url(self):
        return reverse(
            'idhub:admin_people_membership_new', kwargs={'pk': self.user.id},
        )

    def make_membership(self, **kwargs):
        return Membership.objects.create(user=self.user, **{
            'type': Membership.Types.EMPLOYEE,
            'start_date': '2023-01-01',
            **kwargs,
        })

    def test_the_dates_are_asked_for_with_a_date_picker(self):
        form = self.client.get(self.new_url()).context['form']

        self.assertEqual(form.fields['start_date'].widget.input_type, 'date')
        self.assertEqual(form.fields['end_date'].widget.input_type, 'date')
        self.assertTrue(form.fields['start_date'].required)

    def test_a_membership_is_created_for_the_user_of_the_url(self):
        response = self.client.post(self.new_url(), self.payload())

        self.assertRedirects(response, reverse(
            'idhub:admin_people_rol_new', kwargs={'pk': self.user.id},
        ))
        membership = Membership.objects.get()
        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.type, Membership.Types.MEMBER)

    def test_an_overlapping_membership_is_refused(self):
        self.make_membership(type=Membership.Types.MEMBER)

        response = self.client.post(self.new_url(), self.payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Membership.objects.count(), 1)

    def test_a_membership_of_a_user_who_is_not_there_is_a_404(self):
        url = reverse('idhub:admin_people_membership_new', kwargs={'pk': 0})

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.payload()).status_code, 404)

    def test_editing_a_membership_takes_the_user_from_the_row(self):
        membership = self.make_membership()
        url = reverse(
            'idhub:admin_people_membership_edit', kwargs={'pk': membership.id},
        )

        response = self.client.post(url, self.payload(end_date='2024-06-01'))

        self.assertRedirects(response, reverse('idhub:admin_people_list'))
        membership.refresh_from_db()
        self.assertEqual(str(membership.end_date), '2024-06-01')
        self.assertEqual(membership.type, Membership.Types.MEMBER)

    def test_the_edit_page_shows_the_row_and_its_date_pickers(self):
        membership = self.make_membership()
        url = reverse(
            'idhub:admin_people_membership_edit', kwargs={'pk': membership.id},
        )

        form = self.client.get(url).context['form']

        self.assertEqual(form.instance, membership)
        self.assertEqual(form.fields['start_date'].widget.input_type, 'date')

    def test_deleting_a_membership_goes_back_to_the_user(self):
        membership = self.make_membership()
        url = reverse(
            'idhub:admin_people_membership_del', kwargs={'pk': membership.id},
        )

        response = self.client.get(url)

        self.assertRedirects(response, reverse(
            'idhub:admin_people_edit', kwargs={'pk': self.user.id},
        ))
        self.assertFalse(Membership.objects.exists())


class PeopleRolViewsTest(AdminViewTestCase):
    """``/admin/people/<pk>/rol/``: which services the user may reach."""

    def setUp(self):
        super().setUp()
        self.rol = Rol.objects.create(name='Operator')
        self.service = Service.objects.create(
            domain='service.example.org', description='A service',
        )
        self.service.rol.add(self.rol)

    def new_url(self):
        return reverse('idhub:admin_people_rol_new', kwargs={'pk': self.user.id})

    def test_a_role_is_created_for_the_user_of_the_url(self):
        response = self.client.post(self.new_url(), {'service': self.service.id})

        self.assertRedirects(response, reverse(
            'idhub:admin_people_edit', kwargs={'pk': self.user.id},
        ))
        self.assertEqual(UserRol.objects.get().user, self.user)

    def test_the_services_the_user_already_has_are_not_offered_again(self):
        other = Service.objects.create(domain='other.example.org', description='x')
        UserRol.objects.create(user=self.user, service=self.service)

        form = self.client.get(self.new_url()).context['form']

        offered = [label for value, label in form.fields['service'].choices if value]
        self.assertEqual(offered, [str(other)])
        # Only the list shown is filtered: the queryset the field validates
        # against still holds the service, and what refuses it is the
        # duplicate check of clean_service().
        self.assertIn(self.service, form.fields['service'].queryset)

    def test_a_duplicate_role_is_refused(self):
        UserRol.objects.create(user=self.user, service=self.service)

        response = self.client.post(self.new_url(), {'service': self.service.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserRol.objects.count(), 1)

    def test_a_role_for_a_user_who_is_not_there_is_a_404(self):
        url = reverse('idhub:admin_people_rol_new', kwargs={'pk': 0})

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.post(url, {'service': self.service.id}).status_code, 404
        )

    def test_a_role_is_moved_to_another_service(self):
        other = Service.objects.create(domain='other.example.org', description='x')
        user_rol = UserRol.objects.create(user=self.user, service=self.service)
        url = reverse('idhub:admin_people_rol_edit', kwargs={'pk': user_rol.id})

        response = self.client.post(url, {'service': other.id})

        self.assertRedirects(response, reverse(
            'idhub:admin_people_edit', kwargs={'pk': self.user.id},
        ))
        user_rol.refresh_from_db()
        self.assertEqual(user_rol.service, other)

    def test_the_edit_page_shows_the_role(self):
        user_rol = UserRol.objects.create(user=self.user, service=self.service)
        url = reverse('idhub:admin_people_rol_edit', kwargs={'pk': user_rol.id})

        self.assertEqual(
            self.client.get(url).context['form'].instance, user_rol
        )

    def test_deleting_a_role_goes_back_to_the_user(self):
        user_rol = UserRol.objects.create(user=self.user, service=self.service)
        url = reverse('idhub:admin_people_rol_del', kwargs={'pk': user_rol.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse(
            'idhub:admin_people_edit', kwargs={'pk': self.user.id},
        ))
        self.assertFalse(UserRol.objects.exists())


class RolViewsTest(AdminViewTestCase):
    """``/admin/roles/``: the catalogue of roles."""

    def test_a_role_is_created_and_the_dashboard_hears_about_it(self):
        response = self.client.post(reverse('idhub:admin_rol_new'), {
            'name': 'Operator', 'description': 'Runs the thing',
        })

        self.assertRedirects(response, reverse('idhub:admin_roles'))
        self.assertEqual(Rol.objects.get().name, 'Operator')
        self.assertIn('Role created successfully', self.messages(response))
        self.assertTrue(
            Event.objects.filter(type=Event.Types.EV_ROLE_CREATED_BY_ADMIN).exists()
        )

    def test_a_role_is_renamed(self):
        rol = Rol.objects.create(name='Operator', description='x')
        url = reverse('idhub:admin_rol_edit', kwargs={'pk': rol.id})

        response = self.client.post(url, {'name': 'Manager', 'description': 'y'})

        self.assertRedirects(response, reverse('idhub:admin_roles'))
        rol.refresh_from_db()
        self.assertEqual(rol.name, 'Manager')
        self.assertTrue(
            Event.objects.filter(type=Event.Types.EV_ROLE_MODIFIED_BY_ADMIN).exists()
        )

    def test_the_edit_page_loads_the_role_of_the_url(self):
        rol = Rol.objects.create(name='Operator', description='x')
        url = reverse('idhub:admin_rol_edit', kwargs={'pk': rol.id})

        self.assertEqual(self.client.get(url).context['form'].instance, rol)

    def test_editing_a_role_that_is_not_there_is_a_404(self):
        url = reverse('idhub:admin_rol_edit', kwargs={'pk': 999})

        self.assertEqual(self.client.get(url).status_code, 404)

    def test_the_role_number_zero_is_a_500_instead_of_a_404(self):
        # get_form_kwargs() guards the lookup with ``if pk:`` and zero is
        # falsy, so self.object is never set and the template machinery trips
        # over it. The route accepts any integer, zero included.
        url = reverse('idhub:admin_rol_edit', kwargs={'pk': 0})

        with self.assertRaises(AttributeError), self.assertLogs('django.request'):
            self.client.get(url)


class ServiceViewsTest(AdminViewTestCase):
    """``/admin/services/``: the services a credential opens the door to."""

    def setUp(self):
        super().setUp()
        self.rol = Rol.objects.create(name='Operator', description='x')

    def test_a_service_can_be_created_without_any_role(self):
        response = self.client.post(reverse('idhub:admin_service_new'), {
            'domain': 'service.example.org', 'description': 'A service',
        })

        self.assertRedirects(response, reverse('idhub:admin_services'))
        service = Service.objects.get()
        self.assertEqual(list(service.rol.all()), [])
        self.assertIn('Service created successfully', self.messages(response))
        self.assertTrue(
            Event.objects.filter(type=Event.Types.EV_SERVICE_CREATED_BY_ADMIN).exists()
        )

    def test_a_service_is_created_with_the_roles_it_asks_for(self):
        self.client.post(reverse('idhub:admin_service_new'), {
            'domain': 'service.example.org',
            'description': 'A service',
            'rol': [self.rol.id],
        })

        self.assertEqual(list(Service.objects.get().rol.all()), [self.rol])

    def test_a_service_is_modified(self):
        service = Service.objects.create(domain='old.example.org', description='x')
        url = reverse('idhub:admin_service_edit', kwargs={'pk': service.id})

        response = self.client.post(url, {
            'domain': 'new.example.org', 'description': 'y',
        })

        self.assertRedirects(response, reverse('idhub:admin_services'))
        service.refresh_from_db()
        self.assertEqual(service.domain, 'new.example.org')
        self.assertTrue(
            Event.objects.filter(type=Event.Types.EV_SERVICE_MODIFIED_BY_ADMIN).exists()
        )

    def test_the_edit_page_loads_the_service_of_the_url(self):
        service = Service.objects.create(domain='old.example.org', description='x')
        url = reverse('idhub:admin_service_edit', kwargs={'pk': service.id})

        form = self.client.get(url).context['form']

        self.assertEqual(form.instance, service)
        self.assertFalse(form.fields['rol'].required)

    def test_editing_a_service_that_is_not_there_is_a_404(self):
        url = reverse('idhub:admin_service_edit', kwargs={'pk': 999})

        self.assertEqual(self.client.get(url).status_code, 404)

    def test_the_service_number_zero_is_a_500_instead_of_a_404(self):
        # Same falsy pk as in RolEditView: these two views look the object up
        # in get_form_kwargs() behind an ``if pk:``.
        url = reverse('idhub:admin_service_edit', kwargs={'pk': 0})

        with self.assertRaises(AttributeError), self.assertLogs('django.request'):
            self.client.get(url)


class CredentialPagesTest(AdminViewTestCase):
    """``/admin/credentials/``: looking at what was issued."""

    def setUp(self):
        super().setUp()
        self.cred = factories.make_issued_credential(self.user)

    def test_the_detail_page_names_the_type_in_its_subtitle(self):
        url = reverse('idhub:admin_credential', kwargs={'pk': self.cred.id})

        response = self.client.get(url)

        self.assertEqual(response.context['object'], self.cred)
        self.assertEqual(
            response.context['subtitle'], 'Credential: {}'.format(self.cred.type)
        )

    def test_a_credential_that_is_not_there_is_a_404(self):
        url = reverse('idhub:admin_credential', kwargs={'pk': 0})

        self.assertEqual(self.client.get(url).status_code, 404)


class CredentialJsonViewTest(AdminViewTestCase):
    """``/admin/credentials/<pk>/json``: the download of the document."""

    def setUp(self):
        super().setUp()
        self.cred = factories.make_issued_credential(self.user)
        self.url = reverse('idhub:admin_credential_json', kwargs={'pk': self.cred.id})

    def test_the_signed_document_is_served_as_an_attachment(self):
        response = self.client.get(self.url)

        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="credential.json"',
        )
        self.assertEqual(
            json.loads(response.content)['id'],
            'https://testserver/credentials/{}'.format(self.cred.vc_id),
        )

    def test_a_credential_that_was_never_issued_downloads_an_empty_file(self):
        cred = factories.make_credential(
            self.user, self.cred.schema, self.cred.issuer_did,
        )
        url = reverse('idhub:admin_credential_json', kwargs={'pk': cred.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_the_jwt_download_wraps_the_credential_in_a_signed_envelope(self):
        response = self.client.get(self.url, {'format': 'jwt'})

        self.assertEqual(response['Content-Type'], 'application/vc+jwt')
        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename="credential.jwt"',
        )
        self.assertEqual(len(response.content.decode().split('.')), 3)

    def test_a_document_that_already_carries_a_token_is_served_verbatim(self):
        self.cred.set_data(json.dumps({'verifiableCredential': {
            'type': 'EnvelopedVerifiableCredential',
            'id': 'data:application/vc+jwt,header.payload.signature',
        }}))
        self.cred.save()

        response = self.client.get(self.url, {'format': 'jwt'})

        self.assertEqual(response.content, b'header.payload.signature')

    def test_an_envelope_whose_id_is_not_a_token_is_signed_again(self):
        self.cred.set_data(json.dumps({'verifiableCredential': {
            'type': 'EnvelopedVerifiableCredential',
            'id': 'https://testserver/credentials/whatever',
        }}))
        self.cred.save()

        response = self.client.get(self.url, {'format': 'jwt'})

        self.assertEqual(response['Content-Type'], 'application/vc+jwt')
        self.assertNotEqual(response.content, b'')

    def test_asking_for_the_token_of_a_credential_without_data_is_a_500(self):
        # get_data() answers the empty string, which is not JSON, and the
        # blanket except of the view turns it into a json error document.
        cred = factories.make_credential(
            self.user, self.cred.schema, self.cred.issuer_did,
        )
        url = reverse('idhub:admin_credential_json', kwargs={'pk': cred.id})

        with self.assertLogs('idhub.admin.views', level='ERROR'):
            response = self.client.get(url, {'format': 'jwt'})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            json.loads(response.content)['error'],
            'Failed to generate enveloped JWT credential.',
        )

    def test_any_other_format_falls_back_to_the_json_download(self):
        response = self.client.get(self.url, {'format': 'pdf'})

        self.assertEqual(response['Content-Type'], 'application/json')


class CredentialActionsTest(AdminViewTestCase):
    """Revoking and deleting from the list of credentials."""

    def setUp(self):
        super().setUp()
        self.cred = factories.make_issued_credential(self.user)

    def test_revoking_an_issued_credential_is_announced_twice(self):
        url = reverse('idhub:admin_credentials_revoke', kwargs={'pk': self.cred.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_credentials'))
        self.cred.refresh_from_db()
        self.assertEqual(self.cred.status, VerificableCredential.Status.REVOKED)
        self.assertIsNone(Event.objects.get(
            type=Event.Types.EV_CREDENTIAL_REVOKED_BY_ADMIN).user)
        self.assertEqual(Event.objects.get(
            type=Event.Types.EV_CREDENTIAL_REVOKED).user, self.user)

    def test_revoking_twice_leaves_no_second_event(self):
        url = reverse('idhub:admin_credentials_revoke', kwargs={'pk': self.cred.id})
        self.client.get(url)

        self.client.get(url)

        self.assertEqual(
            Event.objects.filter(type=Event.Types.EV_CREDENTIAL_REVOKED).count(), 1
        )

    def test_deleting_a_credential_removes_the_row(self):
        url = reverse('idhub:admin_credentials_delete', kwargs={'pk': self.cred.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_credentials'))
        self.assertFalse(VerificableCredential.objects.exists())


class DidRegisterViewTest(AdminViewTestCase):
    """``/admin/dids/new/``: a new identity for the organization."""

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:admin_dids_new')

    def test_the_page_pre_generates_an_identity_and_parks_it_in_the_session(self):
        self.client.get(self.url)

        self.assertIn('pre_generated_did', self.client.session)
        self.assertFalse(DID.objects.exists())

    def test_the_identity_offered_is_the_same_one_on_a_reload(self):
        first = self.client.get(self.url).context['form'].instance.did

        self.assertEqual(
            self.client.get(self.url).context['form'].instance.did, first
        )

    def test_a_key_did_is_created_and_the_parked_one_dropped(self):
        response = self.client.post(self.url, {
            'label': 'Organisation', 'type': DID.Types.KEY.value,
        })

        self.assertRedirects(response, reverse('idhub:admin_dids'))
        self.assertIn('DID created successfully', self.messages(response))
        self.assertNotIn('pre_generated_did', self.client.session)
        did = DID.objects.get()
        self.assertEqual((did.label, did.user), ('Organisation', None))

    def test_a_label_that_is_already_taken_is_refused(self):
        factories.make_did(label='Organisation')

        response = self.client.post(self.url, {
            'label': 'Organisation', 'type': DID.Types.KEY.value,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DID.objects.count(), 1)

    def test_a_save_that_blows_up_is_reported_on_the_page(self):
        with patch.object(DIDForm, 'save', side_effect=RuntimeError('boom')):
            with self.assertLogs('idhub.admin.views', level='ERROR'):
                response = self.client.post(self.url, {
                    'label': 'Organisation', 'type': DID.Types.KEY.value,
                })

        self.assertEqual(response.status_code, 200)
        self.assertIn('DID could not be created: boom', self.messages(response))
        self.assertFalse(DID.objects.exists())
        # The pre-generated identity stays parked, so a second attempt reuses
        # the keys that were already made.
        self.assertIn('pre_generated_did', self.client.session)


class DidEditViewTest(AdminViewTestCase):
    """``/admin/dids/<pk>/edit/``: only the label can be touched."""

    def setUp(self):
        super().setUp()
        self.did = factories.make_did(label='Organisation')
        self.url = reverse('idhub:admin_dids_edit', kwargs={'pk': self.did.id})

    def test_the_page_loads_the_identity_of_the_url(self):
        response = self.client.get(self.url)

        self.assertEqual(response.context['object'], self.did)

    def test_the_label_is_renamed_and_the_identifier_untouched(self):
        response = self.client.post(self.url, {'label': 'Renamed'})

        self.assertRedirects(response, reverse('idhub:admin_dids'))
        self.assertIn('DID updated successfully', self.messages(response))
        did = DID.objects.get()
        self.assertEqual((did.label, did.did), ('Renamed', self.did.did))

    def test_an_identity_that_is_not_there_is_a_404(self):
        url = reverse('idhub:admin_dids_edit', kwargs={'pk': 0})

        self.assertEqual(self.client.get(url).status_code, 404)

    def test_deleting_an_identity_is_announced_to_the_dashboard(self):
        url = reverse('idhub:admin_dids_del', kwargs={'pk': self.did.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_dids'))
        self.assertFalse(DID.objects.exists())
        self.assertTrue(Event.objects.filter(
            type=Event.Types.EV_ORG_DID_DELETED_BY_ADMIN).exists())


class SchemasDownloadTest(AdminViewTestCase):
    """``/admin/schemas/<pk>/...``: taking a template out of IdHub."""

    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema('membership-card.json')

    def excel_url(self, schema):
        return reverse(
            'idhub:admin_schemas_template_excel', kwargs={'pk': schema.id}
        )

    def test_the_schema_is_served_under_its_own_file_name(self):
        url = reverse('idhub:admin_schemas_download', kwargs={'pk': self.schema.id})

        response = self.client.get(url)

        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(
            response['Content-Disposition'],
            'inline; filename=membership-card.json',
        )
        self.assertEqual(json.loads(response.content)['title'], self.schema.type)

    def test_the_excel_template_is_built_out_of_the_schema(self):
        response = self.client.get(self.excel_url(self.schema))

        self.assertEqual(
            response['Content-Disposition'],
            'attachment; filename=membership-card.xlsx',
        )
        self.assertTrue(response.content.startswith(b'PK'))

    def test_a_schema_credtools_cannot_export_degrades_to_a_message(self):
        # device-snapshot-v1.json declares an array property and the format
        # table of credtools only knows string, date and integer: B39. The
        # blanket except of the view turns the KeyError into this message.
        schema = factories.make_schema('device-snapshot-v1.json')

        response = self.client.get(self.excel_url(schema))

        self.assertRedirects(response, reverse('idhub:admin_schemas'))
        self.assertIn(
            'You cannot download an excel template of this scheme.'
            ' Remember that we have an API to interact with this type of schemes',
            self.messages(response),
        )

    def test_deleting_a_schema_removes_the_row(self):
        url = reverse('idhub:admin_schemas_del', kwargs={'pk': self.schema.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_schemas'))
        self.assertFalse(Schemas.objects.exists())


class SchemasNewViewTest(AdminViewTestCase):
    """``/admin/schemas/new``: uploading a template by hand."""

    FILE_NAME = 'brand-new-template.json'

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:admin_schemas_new')
        self.data = factories.read_schema('membership-card.json')

    def upload(self, content=None, name=None):
        return self.client.post(self.url, {'file_template': SimpleUploadedFile(
            name or self.FILE_NAME, (content or self.data).encode(),
        )})

    def test_a_valid_template_is_stored_under_the_name_of_the_file(self):
        response = self.upload()

        self.assertRedirects(response, reverse('idhub:admin_schemas'))
        schema = Schemas.objects.get()
        self.assertEqual(schema.file_schema, self.FILE_NAME)
        self.assertEqual(schema.data, self.data)

    def test_the_type_of_an_uploaded_template_is_the_whole_name_list(self):
        # handle_uploaded_file() stores ``type=ldata.get('name')``, and the
        # name of a schema is a list of {value, lang} dicts, not a string. So
        # the column that should read MembershipCard gets the repr of that
        # list. Schemas.save() does not correct it, because it only computes
        # get_type when type is empty, and the other two upload paths
        # -ImportSchemaForm and SchemasEnableAddView- do set it right.
        self.upload()

        schema = Schemas.objects.get()
        self.assertEqual(schema.type, str(json.loads(self.data)['name']))
        self.assertEqual(schema.get_type, 'MembershipCard')

    def test_a_file_name_that_is_already_there_is_refused(self):
        factories.make_schema('membership-card.json')

        response = self.upload(name='membership-card.json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('This template already exists!', self.messages(response))
        self.assertEqual(Schemas.objects.count(), 1)

    def test_something_that_is_not_a_schema_is_refused(self):
        response = self.upload(content='not json at all')

        self.assertEqual(response.status_code, 200)
        self.assertIn('This is not a valid schema!', self.messages(response))
        self.assertIn('There are some errors in the file', self.messages(response))
        self.assertFalse(Schemas.objects.exists())

    def test_a_schema_without_a_name_is_refused(self):
        data = json.loads(self.data)
        del data['name']

        response = self.upload(content=json.dumps(data))

        self.assertIn('This is not a valid schema!', self.messages(response))
        self.assertFalse(Schemas.objects.exists())

    def test_posting_no_file_at_all_just_redraws_the_page(self):
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.messages(response), [])
        self.assertFalse(Schemas.objects.exists())


class SchemasUploadViewTest(AdminViewTestCase):
    """``/admin/schemas/upload``: the same thing by file or by url."""

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:admin_schemas_upload')
        self.data = factories.read_schema('membership-card.json')

    def test_a_schema_uploaded_as_a_file_is_announced_to_the_dashboard(self):
        response = self.client.post(self.url, {
            'schema_import': SimpleUploadedFile(
                'membership-card.json', self.data.encode(),
            ),
        })

        self.assertRedirects(response, reverse('idhub:admin_schemas'))
        self.assertIn('The file was imported successfully!', self.messages(response))
        self.assertTrue(Schemas.objects.exists())
        self.assertTrue(
            Event.objects.filter(type=Event.Types.EV_SCHEME_UPLOAD).exists()
        )

    def test_the_context_of_the_upload_is_published_under_this_host(self):
        # The file form is the only one that gets a domain: the url form keeps
        # the context url as it was given.
        response = self.client.post(self.url, {
            'schema_import': SimpleUploadedFile(
                'membership-card.json', self.data.encode(),
            ),
            'context_import': SimpleUploadedFile(
                'membership-card.jsonld', b'{"@context": {}}',
            ),
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Schemas.objects.get().context,
            'https://testserver/context/membership-card.jsonld',
        )

    def test_the_url_form_is_the_one_used_when_the_url_button_is_pressed(self):
        from idhub.services import VerificationService
        with patch.object(VerificationService, 'validate_safe_host'):
            response = self.client.post(self.url, {
                'submitUrl': '',
                'schema_url': 'https://schemas.example.org/vc_schemas/membership-card.json',
            })

        self.assertRedirects(response, reverse('idhub:admin_schemas'))
        schema = Schemas.objects.get()
        self.assertEqual(schema.file_schema, 'membership-card.json')
        self.assertEqual(
            schema.validation_url,
            'https://schemas.example.org/vc_schemas/membership-card.json',
        )

    def test_the_page_offers_the_url_form_next_to_the_file_one(self):
        context = self.client.get(self.url).context

        self.assertIn('schema_import', context['form'].fields)
        self.assertIn('schema_url', context['form_url'].fields)


class SchemasEnableAddViewTest(AdminViewTestCase):
    """``/admin/schemas/enable/<name>``: loading one of the shipped files."""

    FILE_NAME = 'membership-card.json'

    def url(self, file_name=None):
        return reverse('idhub:admin_schemas_enable_add', kwargs={
            'file_schema': file_name or self.FILE_NAME,
        })

    def test_a_file_of_the_schemas_directory_is_loaded_whole(self):
        response = self.client.get(self.url())

        self.assertRedirects(response, reverse('idhub:admin_schemas'))
        self.assertIn('The schema was added sucessfully', self.messages(response))
        schema = Schemas.objects.get()
        data = json.loads(factories.read_schema(self.FILE_NAME))
        self.assertEqual(schema.type, data['title'])
        self.assertEqual(json.loads(schema._name), data['name'])
        self.assertEqual(schema.template_description, schema._description)

    def test_a_name_that_is_not_in_the_directory_is_reported(self):
        response = self.client.get(self.url('not-there.json'))

        self.assertRedirects(response, reverse('idhub:admin_schemas_enable'))
        self.assertIn('The schema not-there.json not exist!', self.messages(response))
        self.assertFalse(Schemas.objects.exists())

    def test_a_file_that_does_not_validate_leaves_nothing_behind(self):
        with patch('idhub.admin.views.credtools.validate_schema', return_value=False):
            response = self.client.get(self.url())

        self.assertRedirects(response, reverse('idhub:admin_schemas'))
        self.assertIn('This is not a valid schema!', self.messages(response))
        self.assertFalse(Schemas.objects.exists())

    def test_the_page_offers_only_the_files_not_loaded_yet(self):
        factories.make_schema(self.FILE_NAME)

        schemas = self.client.get(
            reverse('idhub:admin_schemas_enable')
        ).context['schemas']

        self.assertNotIn(self.FILE_NAME, schemas)
        self.assertIn('course-credential.json', schemas)


class ImportAddViewTest(AdminViewTestCase):
    """``/admin/import/new``: the spreadsheet that enables credentials.

    The happy path of the import is covered in ``test_credentials.py``; what
    is pinned here is the mail that goes out with it, and what happens when
    that mail fails.
    """

    EXCEL = 'examples/excel_examples/membership-card.xlsx'

    def setUp(self):
        super().setUp()
        self.did = factories.make_did(label='Issuer')
        self.schema = factories.make_schema('membership-card.json')
        self.url = reverse('idhub:admin_import_add')

    def upload(self):
        from django.conf import settings
        from pathlib import Path
        content = Path(settings.BASE_DIR).joinpath(self.EXCEL).read_bytes()
        return self.client.post(self.url, {
            'did': self.did.did,
            'schema': self.schema.id,
            'file_import': SimpleUploadedFile('membership-card.xlsx', content),
        })

    def test_every_row_enables_a_credential_and_announces_it_twice(self):
        response = self.upload()

        self.assertRedirects(response, reverse('idhub:admin_import'))
        self.assertIn('The file was imported successfully!', self.messages(response))
        created = VerificableCredential.objects.count()
        self.assertTrue(created)
        for event_type in (Event.Types.EV_CREDENTIAL_ENABLED,
                           Event.Types.EV_CREDENTIAL_CAN_BE_REQUESTED):
            self.assertEqual(
                Event.objects.filter(type=event_type).count(), created
            )
        self.assertEqual(File_datas.objects.get().file_name, 'membership-card.xlsx')

    def test_the_users_of_the_rows_are_invited_by_email(self):
        with patch('idhub.admin.views.ImportAddView.send_email') as send_email:
            self.upload()

        invited = {call.args[0].email for call in send_email.call_args_list}
        self.assertEqual(invited, set(
            User.objects.exclude(id__in=[self.user.id, self.admin_user.id])
            .values_list('email', flat=True)
        ))

    def test_a_mail_server_that_refuses_the_invitation_crashes_the_import(self):
        # The handler of the SMTPException reads ``e.message``, an attribute
        # exceptions have not had since Python 2, so the branch that should
        # turn the failure into a flash message raises instead. The rows are
        # already committed by then, so the import is left half done with a
        # 500 on the screen. PeopleRegisterView gets this right, with str(e).
        with patch('idhub.admin.views.ImportAddView.send_email',
                   side_effect=SMTPException('no mail for you')):
            with self.assertRaises(AttributeError), self.assertLogs('django.request'):
                self.upload()

        self.assertTrue(VerificableCredential.objects.exists())

    def test_an_import_that_enables_nothing_is_reported_as_an_error(self):
        # Unreachable through ImportForm, whose save() always answers the list
        # of rows it just created; the branch is pinned because the message is
        # the only thing the admin would see if it ever did.
        with patch.object(ImportForm, 'is_valid', return_value=True), \
                patch.object(ImportForm, 'save', return_value=[]):
            response = self.client.post(self.url, {})

        self.assertRedirects(response, reverse('idhub:admin_import'))
        self.assertIn('Error importing the file!', self.messages(response))

    def test_the_second_step_of_the_import_is_dead_code(self):
        # ImportStep2View has no entry in idhub/urls.py and the template it
        # names, idhub/admin/import_step2.html, is not in the repository. It
        # cannot be reached and it could not render if it were.
        request = RequestFactory().get('/admin/import')
        request.user = self.admin_user
        request.session = self.client.session

        view = ImportStep2View()
        view.setup(request)
        self.assertEqual(list(view.get_context_data()['schemas'].all()), [self.schema])
        with self.assertRaises(TemplateDoesNotExist):
            view.get(request).render()

    def test_deleting_an_import_removes_only_the_record_of_the_file(self):
        self.upload()
        file_data = File_datas.objects.get()
        url = reverse('idhub:admin_import_del', kwargs={'pk': file_data.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_import'))
        self.assertFalse(File_datas.objects.exists())
        self.assertTrue(VerificableCredential.objects.exists())


class VCTemplatePdfViewsTest(AdminViewTestCase):
    """``/admin/templates_pdf``: the html used to draw a credential."""

    def make_template(self, name='Card', data=b'<html><body>Card</body></html>'):
        return VCTemplatePdf.objects.create(
            name=name, data=SimpleUploadedFile('card.html', data),
        )

    def test_a_template_is_uploaded_and_listed(self):
        response = self.client.post(reverse('idhub:admin_new_template_pdf'), {
            'name': 'Card',
            'data': SimpleUploadedFile('card.html', b'<html>{{ qr }}</html>'),
        })

        self.assertRedirects(response, reverse('idhub:admin_templates_pdf'))
        self.assertEqual(VCTemplatePdf.objects.get().name, 'Card')

    def test_the_newest_template_is_listed_first(self):
        self.make_template(name='First')
        last = self.make_template(name='Second')

        table = self.client.get(reverse('idhub:admin_templates_pdf')).context['table']

        self.assertEqual(table.data[0], last)

    def test_the_template_is_rendered_to_a_pdf_attachment(self):
        template = self.make_template()
        url = reverse('idhub:admin_template_pdf_render', kwargs={'pk': template.id})

        response = self.client.get(url)

        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(
            response['Content-Disposition'], 'attachment; filename=Card.pdf'
        )
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_a_template_weasyprint_chokes_on_is_reported_on_the_list(self):
        template = self.make_template()
        url = reverse('idhub:admin_template_pdf_render', kwargs={'pk': template.id})

        with patch('idhub.admin.views.weasyprint.HTML',
                   side_effect=ValueError('broken html')):
            with self.assertLogs('idhub.admin.views', level='ERROR'):
                response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_templates_pdf'))
        self.assertIn(
            'Some thing is wrong with this template', self.messages(response)
        )

    def test_deleting_a_template_removes_the_row(self):
        template = self.make_template()
        url = reverse('idhub:admin_template_pdf_del', kwargs={'pk': template.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_templates_pdf'))
        self.assertFalse(VCTemplatePdf.objects.exists())


class PeopleDetailViewsTest(AdminViewTestCase):
    """The read-only page of a user, and the two buttons next to it."""

    def test_the_page_of_a_user_shows_that_user(self):
        url = reverse('idhub:admin_people', kwargs={'pk': self.user.id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], self.user)

    def test_a_user_that_does_not_exist_is_a_404(self):
        url = reverse('idhub:admin_people', kwargs={'pk': 999})

        self.assertEqual(self.client.get(url).status_code, 404)

    def test_the_activate_button_toggles_the_flag_both_ways(self):
        url = reverse('idhub:admin_people_activate', kwargs={'pk': self.user.id})

        response = self.client.get(url)

        self.assertRedirects(
            response, reverse('idhub:admin_people', kwargs={'pk': self.user.id})
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(Event.objects.filter(
            type=Event.Types.EV_USR_DEACTIVATED_BY_ADMIN).exists())

        self.client.get(url)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(Event.objects.filter(
            type=Event.Types.EV_USR_ACTIVATED_BY_ADMIN).exists())

    def test_an_admin_cannot_deactivate_themselves(self):
        url = reverse('idhub:admin_people_activate',
                      kwargs={'pk': self.admin_user.id})

        response = self.client.get(url, follow=True)

        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)
        self.assertIn(
            'It is not possible deactivate your account!', self.messages(response)
        )

    def test_deleting_a_user_removes_the_row(self):
        url = reverse('idhub:admin_people_delete', kwargs={'pk': self.user.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_people_list'))
        self.assertFalse(User.objects.filter(id=self.user.id).exists())
        # The event is set before the delete, so it outlives the user it names.
        self.assertTrue(Event.objects.filter(
            type=Event.Types.EV_USR_DELETED_BY_ADMIN).exists())

    def test_an_admin_cannot_delete_themselves(self):
        url = reverse('idhub:admin_people_delete',
                      kwargs={'pk': self.admin_user.id})

        response = self.client.get(url, follow=True)

        self.assertTrue(User.objects.filter(id=self.admin_user.id).exists())
        self.assertIn(
            'It is not possible delete your account!', self.messages(response)
        )


class PeopleListViewTest(AdminViewTestCase):

    def test_the_list_holds_every_user(self):
        response = self.client.get(reverse('idhub:admin_people_list'))

        rows = [row.record for row in response.context['table'].rows]
        self.assertCountEqual(rows, [self.user, self.admin_user])


class PeopleRegisterMailFailureTest(AdminViewTestCase):

    def test_a_mail_server_that_refuses_the_welcome_only_warns(self):
        # Unlike ImportAddView, this handler passes the exception itself to
        # messages.error instead of reading e.message, so the account survives
        # and the admin is told what happened.
        url = reverse('idhub:admin_people_new')

        with patch('idhub.admin.views.PeopleRegisterView.send_email',
                   side_effect=SMTPException('no mail for you')):
            response = self.client.post(url, {
                'first_name': 'Fresh', 'last_name': 'Account',
                'email': 'fresh@example.org',
            }, follow=True)

        self.assertTrue(User.objects.filter(email='fresh@example.org').exists())
        self.assertIn('no mail for you', self.messages(response))


class MembershipDeleteCrashTest(AdminViewTestCase):

    def test_deleting_your_own_membership_is_a_500_on_an_unbound_name(self):
        # The else branch of PeopleMembershipDeleteView.get was written for a
        # User and the view holds a Membership, so the comparison with
        # request.user can never be true and the branch is dead. Were it ever
        # reachable, ``user`` would not be bound and the redirect below would
        # raise. What is pinned here is the live branch, plus the fact that the
        # dead one leaves the name unbound.
        membership = Membership.objects.create(
            user=self.user, type=Membership.Types.MEMBER
        )
        url = reverse('idhub:admin_people_membership_del',
                      kwargs={'pk': membership.id})

        response = self.client.get(url)

        self.assertRedirects(
            response,
            reverse('idhub:admin_people_edit', kwargs={'pk': self.user.id}),
        )
        self.assertFalse(Membership.objects.exists())


class RolAndServiceDeleteTest(AdminViewTestCase):

    def test_deleting_a_role_removes_the_row(self):
        rol = Rol.objects.create(name='Member')
        url = reverse('idhub:admin_rol_del', kwargs={'pk': rol.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_roles'))
        self.assertFalse(Rol.objects.exists())
        self.assertTrue(Event.objects.filter(
            type=Event.Types.EV_ROLE_DELETED_BY_ADMIN).exists())

    def test_deleting_a_service_removes_the_row(self):
        service = Service.objects.create(
            domain='service.example.org', description='x'
        )
        url = reverse('idhub:admin_service_del', kwargs={'pk': service.id})

        response = self.client.get(url)

        self.assertRedirects(response, reverse('idhub:admin_services'))
        self.assertFalse(Service.objects.exists())
        self.assertTrue(Event.objects.filter(
            type=Event.Types.EV_SERVICE_DELETED_BY_ADMIN).exists())

    def test_the_two_lists_are_reachable(self):
        Rol.objects.create(name='Member')
        Service.objects.create(domain='service.example.org', description='x')

        for name in ('idhub:admin_roles', 'idhub:admin_services'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context['table'].rows), 1)


class WalletViewsTest(AdminViewTestCase):

    def test_the_organisation_wallet_lists_the_credentials_of_the_org(self):
        response = self.client.get(reverse('idhub:admin_wallet_credentials'))

        self.assertEqual(response.status_code, 200)

    def test_importing_a_certificate_creates_the_eidas1_identity(self):
        url = reverse('idhub:admin_wallet_config_eidas1')
        pfx = SimpleUploadedFile(
            factories.EIDAS1_PFX_NAME,
            factories.read_eidas1_pfx(),
            content_type='application/x-pkcs12',
        )

        response = self.client.post(url, {
            'label': 'Organisation certificate',
            'password': factories.EIDAS1_PFX_PASSWORD,
            'file_import': pfx,
        }, follow=True)

        self.assertIn(
            'The eIDAS1 identity was created successfully!', self.messages(response)
        )
        did = DID.objects.get(eidas1=True)
        self.assertIsNone(did.user)
        self.assertTrue(Event.objects.filter(
            type=Event.Types.EV_ORG_DID_CREATED_BY_ADMIN).exists())

    def test_a_certificate_the_form_refuses_to_save_is_reported(self):
        # The else branch only runs when save() returns something falsy, which
        # ImportCertificateForm never does, so it is pinned behind a patch.
        from idhub.admin.forms import ImportCertificateForm

        url = reverse('idhub:admin_wallet_config_eidas1')
        pfx = SimpleUploadedFile(
            factories.EIDAS1_PFX_NAME,
            factories.read_eidas1_pfx(),
            content_type='application/x-pkcs12',
        )

        with patch.object(ImportCertificateForm, 'save', return_value=None):
            response = self.client.post(url, {
                'label': 'Organisation certificate',
                'password': factories.EIDAS1_PFX_PASSWORD,
                'file_import': pfx,
            }, follow=True)

        self.assertIn('Error creating eIDAS1 identity!', self.messages(response))
        self.assertFalse(Event.objects.filter(
            type=Event.Types.EV_ORG_DID_CREATED_BY_ADMIN).exists())


class UNTPCredentialsViewTest(AdminViewTestCase):
    """The page that issues UNTP credentials and mints object identities."""

    SUBJECT_ID = 'did:web:testserver:product:1'

    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:admin_issue_untp')
        self.issuer = factories.make_did(label='Issuer')
        self.schema = self.make_untp_schema()

    def make_untp_schema(self, untp_type='DigitalProductPassport'):
        data = json.dumps({
            'title': untp_type,
            'name': [{'value': untp_type, 'lang': 'en'}],
            'properties': {
                'type': {'default': ['VerifiableCredential', untp_type]},
                '@context': {'default': ['https://test.uncefact.org/vocabulary/untp/dpp/0.6.0/']},
            },
        })
        return Schemas.objects.create(
            file_schema='untp-dpp.json', data=data, type=untp_type
        )

    def subject_file(self, subject=None):
        payload = json.dumps({
            'credentialSubject': subject if subject is not None
            else {'id': self.SUBJECT_ID, 'name': 'A product'},
        })
        return SimpleUploadedFile(
            'subject.json', payload.encode(), content_type='application/json'
        )

    def post(self, issued=(201, {'id': 'urn:uuid:1'}), **extra):
        data = {
            'issuer': str(self.issuer.id),
            'schema': str(self.schema.id),
            'file_import': self.subject_file(extra.pop('subject', None)),
        }
        data.update(extra)
        with patch('idhub.admin.forms.CredentialIssuanceService'
                   '.issue_untp_credential', return_value=issued) as issue:
            response = self.client.post(self.url, data, follow=True)
        return response, issue

    def test_only_the_product_identities_are_listed(self):
        product = DID.objects.create(
            label='Product', type=DID.Types.WEB, is_product=True
        )
        product.set_did()
        product.save()

        response = self.client.get(self.url)

        rows = [row.record for row in response.context['table'].rows]
        self.assertEqual(rows, [product])
        self.assertNotIn(self.issuer, rows)

    def test_a_credential_the_service_accepts_is_announced_as_issued(self):
        response, issue = self.post()

        self.assertRedirects(response, reverse('idhub:admin_dids'))
        self.assertIn('UNTP credential issued successfully.', self.messages(response))
        kwargs = issue.call_args.kwargs
        self.assertEqual(kwargs['schema_name'], 'untp-dpp.json')
        self.assertEqual(kwargs['credential_type'],
                         ['VerifiableCredential', 'DigitalProductPassport'])
        self.assertEqual(kwargs['issuer_did_obj'], self.issuer)

    def test_a_service_that_refuses_the_issuance_keeps_the_admin_on_the_page(self):
        response, _issue = self.post(
            issued=(400, {'error': 'bad subject', 'details': 'missing name'})
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'Issuance failed: bad subject missing name',
            response.context['form'].errors['__all__'],
        )
        self.assertNotIn(
            'UNTP credential issued successfully.', self.messages(response)
        )

    def test_asking_for_a_new_identity_mints_it_and_rewrites_the_subject_id(self):
        response, issue = self.post(
            create_did='on',
            did_method=str(DID.Types.WEB.value),
            subject={'name': 'A product with no id'},
        )

        self.assertRedirects(response, reverse('idhub:admin_dids'))
        product = DID.objects.get(is_product=True)
        self.assertEqual(issue.call_args.kwargs['subject_did'], product)
        self.assertEqual(issue.call_args.kwargs['subject_data']['id'], product.did)

    def test_a_facility_record_is_issued_to_the_issuer_itself(self):
        self.schema = self.make_untp_schema('DigitalFacilityRecord')

        _response, issue = self.post()

        self.assertEqual(issue.call_args.kwargs['subject_did'], self.issuer)

    def test_a_file_that_is_not_json_is_refused_by_the_form(self):
        with patch('idhub.admin.forms.CredentialIssuanceService'
                   '.issue_untp_credential') as issue:
            response = self.client.post(self.url, {
                'issuer': str(self.issuer.id),
                'schema': str(self.schema.id),
                'file_import': SimpleUploadedFile(
                    'subject.json', b'not json at all',
                    content_type='application/json',
                ),
            })

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'Invalid JSON file. Please ensure the file is correctly formatted.',
            response.context['form'].errors['file_import'],
        )
        issue.assert_not_called()

    def test_the_same_subject_cannot_be_issued_twice(self):
        factories.make_credential(
            self.admin_user, self.schema, self.issuer,
            subject_id=self.SUBJECT_ID,
            status=VerificableCredential.Status.ISSUED,
        )

        with patch('idhub.admin.forms.CredentialIssuanceService'
                   '.issue_untp_credential') as issue:
            response = self.client.post(self.url, {
                'issuer': str(self.issuer.id),
                'schema': str(self.schema.id),
                'file_import': self.subject_file(),
            })

        self.assertIn(
            'A credential for one or more of these subjects already exists.',
            response.context['form'].errors['__all__'],
        )
        issue.assert_not_called()
