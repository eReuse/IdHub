"""Who can reach what.

Authorisation lives in two places. ``UserView`` (``idhub/mixins.py``) refuses
anonymous visitors, and ``AdminView.get``/``post`` bounce a non-admin back to
their own dashboard. The second one only works for views that let
``AdminView`` handle the request: seventeen admin views override ``get``,
call ``check_valid_user()`` as a bare statement and *throw the answer away*.

The url table is read from ``idhub.urls`` instead of being copied, so a new
route that forgets to protect itself turns these tests red.

The user side has a second, independent problem: some of its own views look an
object up by primary key alone, so one user reaches another user's rows through
pages that are otherwise correctly logged-in.
"""
import uuid

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from idhub.models import DID, Event, File_datas, Rol, Service, VCTemplatePdf
from idhub.models import Membership, UserRol, VerificableCredential
from idhub.urls import urlpatterns
from idhub_auth.models import User
from test_support import factories
from test_support.base import IdHubTestCase


# Reachable without logging in: the login pages themselves, the did/context/
# schema documents a verifier needs, and the public credential endpoint.
PUBLIC = {
    'login',
    'logout',
    'password_reset',
    'password_reset_done',
    'password_reset_complete',
    'password_reset_confirm',
    'context',
    'context_file',
    'schema',
    'serve_did',
    'serve_registry_did',
    'public_credential_json',
}

# Protected with a bare @login_required, which defaults to a login url this
# project does not route.
WRONG_LOGIN_URL = {'available_did', 'confirm_send_2f'}

# The one admin view that answers 403 instead of redirecting.
FORBIDS = {'admin_2fauth'}

# Admin views that let AdminView handle the request, so check_valid_user()
# actually bounces a non-admin.
GUARDED = [
    'admin_credentials',
    'admin_dashboard',
    'admin_dids',
    'admin_dids_new',
    'admin_import',
    'admin_import_add',
    'admin_new_template_pdf',
    'admin_people',
    'admin_people_list',
    'admin_people_membership_new',
    'admin_people_new',
    'admin_people_rol_new',
    'admin_rol_new',
    'admin_roles',
    'admin_schemas',
    'admin_schemas_enable',
    'admin_schemas_new',
    'admin_schemas_upload',
    'admin_rol_edit',
    'admin_service_edit',
    'admin_service_new',
    'admin_services',
    'admin_templates_pdf',
    'admin_terms_and_conditions',
    'admin_wallet_config_eidas1',
    'admin_wallet_credentials',
]

# Guarded as well, but they look the object up *before* delegating, so a
# missing row answers 404 and the guard never runs.
GUARDED_AFTER_LOOKUP = [
    'admin_credential',
    'admin_dids_edit',
    'admin_people_edit',
    'admin_people_membership_edit',
    'admin_people_rol_edit',
]

MISSING_PK = 9999

# The seventeen that do not. Every entry here is a live authorisation bypass:
# any logged-in user can reach the admin action behind it.
UNGUARDED = [
    'admin_credential_json',
    'admin_credentials_delete',
    'admin_credentials_revoke',
    'admin_dids_del',
    'admin_import_del',
    'admin_people_activate',
    'admin_people_delete',
    'admin_people_membership_del',
    'admin_people_rol_del',
    'admin_rol_del',
    'admin_schemas_del',
    'admin_schemas_download',
    'admin_schemas_enable_add',
    'admin_schemas_template_excel',
    'admin_service_del',
    'admin_template_pdf_del',
    'admin_template_pdf_render',
]

ARGUMENTS = {'int': 1, 'string': 'x', 'slug': 'x', 'path': 'x',
             'uuid': uuid.uuid4()}


def arguments_for(pattern):
    """One value per url argument, taken from its path converter."""
    return [
        ARGUMENTS[type(converter).__name__.removesuffix('Converter').lower()]
        for converter in pattern.pattern.converters.values()
    ]


def url(name, *args):
    return reverse('idhub:{}'.format(name), args=args)


def every_url():
    for pattern in urlpatterns:
        if pattern.name:
            yield pattern.name, reverse(
                'idhub:{}'.format(pattern.name), args=arguments_for(pattern)
            )


def takes_arguments(name):
    return any(
        pattern.pattern.converters
        for pattern in urlpatterns if pattern.name == name
    )


class AnonymousAccessTest(IdHubTestCase):
    def test_every_private_url_sends_the_visitor_to_the_login_page(self):
        for name, path in every_url():
            if name in PUBLIC or name in WRONG_LOGIN_URL:
                continue
            with self.subTest(url=name):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/login/?next='))

    def test_the_public_urls_answer_without_a_session(self):
        for name, path in every_url():
            if name not in PUBLIC:
                continue
            with self.subTest(url=name):
                response = self.client.get(path)
                self.assertNotEqual(response.status_code, 403)
                if response.status_code == 302:
                    self.assertNotIn('/login/?next=', response['Location'])

    def test_two_urls_point_at_a_login_page_the_project_does_not_have(self):
        # AvailableDidView and DobleFactorSendView use the plain
        # @login_required / LoginRequiredMixin defaults instead of the
        # login_url of UserView, so the visitor lands on a 404.
        for name, path in every_url():
            if name not in WRONG_LOGIN_URL:
                continue
            with self.subTest(url=name):
                response = self.client.get(path)
                self.assertTrue(
                    response['Location'].startswith('/accounts/login/')
                )
        self.assertEqual(self.client.get('/accounts/login/').status_code, 404)

    def test_the_url_table_is_fully_accounted_for(self):
        # So that a new route has to be classified instead of silently
        # escaping the matrix above.
        named = {name for name, _path in every_url()}
        classified = (
            PUBLIC | WRONG_LOGIN_URL | FORBIDS | set(GUARDED)
            | set(GUARDED_AFTER_LOOKUP) | set(UNGUARDED)
        )
        user_side = {name for name in named if not name.startswith('admin_')}

        self.assertEqual(named - classified - user_side, set())
        self.assertFalse(set(GUARDED) & set(UNGUARDED))
        self.assertFalse(set(GUARDED_AFTER_LOOKUP) & set(UNGUARDED))


class PlainUserOnAdminPagesTest(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.user_login()

    def path(self, name):
        return dict(every_url())[name]

    def test_the_guarded_admin_pages_bounce_to_the_user_dashboard(self):
        for name in GUARDED:
            with self.subTest(url=name):
                response = self.client.get(self.path(name))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response['Location'], reverse('idhub:user_dashboard'))

    def test_a_missing_row_is_answered_before_the_guard_runs(self):
        # These views call get_object_or_404 in their own get() and only then
        # delegate, so a plain user gets 404 for a row that does not exist and
        # the dashboard redirect for one that does: the status code tells them
        # which primary keys are in use.
        for name in GUARDED_AFTER_LOOKUP:
            with self.subTest(url=name):
                path = url(name, MISSING_PK)
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_the_only_view_that_answers_forbidden(self):
        # DobleFactorAuthView raises Http403 for a non-admin instead of
        # redirecting, which is the behaviour the rest does not have.
        for name in FORBIDS:
            with self.subTest(url=name):
                self.assertEqual(self.client.get(self.path(name)).status_code, 403)

    def test_the_bounce_explains_itself(self):
        response = self.client.get(reverse('idhub:admin_dashboard'), follow=True)

        self.assertEqual(
            [str(message) for message in response.context['messages']],
            ['User is not authorized to see admin pages, redirected to user '
             'dashboard'],
        )

    def test_a_post_is_guarded_too(self):
        # AdminView.post runs the same check before super().post(), so the
        # usual "GET protected, POST open" hole is not there.
        for name in ('admin_people_new', 'admin_rol_new', 'admin_service_new'):
            with self.subTest(url=name):
                response = self.client.post(self.path(name), data={})
                self.assertEqual(response['Location'], reverse('idhub:user_dashboard'))

        self.assertEqual(User.objects.count(), 2)
        self.assertFalse(Rol.objects.exists())
        self.assertFalse(Service.objects.exists())

    def test_the_unguarded_admin_pages_are_not_bounced(self):
        # The counterpart of the list above: none of these seventeen sends the
        # user back to their dashboard, because the answer of
        # check_valid_user() is discarded. Fixing one makes this red and
        # points at the entry to move into GUARDED.
        for name in UNGUARDED:
            with self.subTest(url=name):
                response = self.client.get(self.path(name))
                location = response.get('Location')
                self.assertNotEqual(location, reverse('idhub:user_dashboard'))


class AdminAccessTest(IdHubTestCase):
    """The third actor of the matrix: the admin actually gets the page."""

    def setUp(self):
        super().setUp()
        self.admin_login()

    def test_every_guarded_page_without_arguments_renders(self):
        for name, path in every_url():
            if name in GUARDED and not takes_arguments(name):
                with self.subTest(url=name):
                    self.assertEqual(self.client.get(path).status_code, 200)


class AuthorizationBypassTest(IdHubTestCase):
    """What a plain user can actually do through those seventeen views."""

    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema('membership-card.json')
        self.victim = factories.make_user('victim@example.org', 'victimpass12')
        # create_user leaves the per-user key unset; the registration views are
        # what build it, so a test that encrypts has to do it by hand.
        self.victim.set_encrypted_sensitive_data()
        self.victim.save()
        self.user_login()

    def test_a_plain_user_can_delete_any_other_user(self):
        self.client.get(url('admin_people_delete', self.victim.id))

        self.assertFalse(User.objects.filter(pk=self.victim.pk).exists())

    def test_a_plain_user_can_deactivate_any_other_user(self):
        self.client.get(url('admin_people_activate', self.victim.id))
        self.victim.refresh_from_db()

        self.assertFalse(self.victim.is_active)

    def test_a_plain_user_can_read_the_credential_of_anyone(self):
        # get_object_or_404 does not filter by user here, and get_data()
        # decrypts with the owner's key, so the body is the plaintext VC.
        credential = factories.make_credential(
            self.victim, self.schema, factories.make_did(label='Issuer')
        )
        credential.set_data('{"the": "credential"}')
        credential.save()

        response = self.client.get(
            url('admin_credential_json', credential.id)
        )
        self.assertEqual(response.content.decode(), '{"the": "credential"}')

    def test_a_plain_user_can_revoke_an_issued_credential(self):
        credential = factories.make_credential(
            self.victim, self.schema, factories.make_did(label='Issuer'),
            status=VerificableCredential.Status.ISSUED,
        )
        self.client.get(url('admin_credentials_revoke', credential.id))
        credential.refresh_from_db()

        self.assertEqual(credential.status, VerificableCredential.Status.REVOKED)

    def test_a_plain_user_can_delete_an_organisation_did(self):
        did = factories.make_did(label='Organisation')
        self.client.get(url('admin_dids_del', did.id))

        self.assertFalse(DID.objects.filter(pk=did.pk).exists())

    def test_a_plain_user_can_delete_a_schema(self):
        self.client.get(url('admin_schemas_del', self.schema.id))

        self.assertFalse(self.schema.__class__.objects.exists())

    def test_a_plain_user_can_download_any_schema(self):
        response = self.client.get(
            url('admin_schemas_download', self.schema.id)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), self.schema.data)

    def test_a_plain_user_can_delete_a_membership_and_a_rol_grant(self):
        membership = Membership.objects.create(
            user=self.victim, type=Membership.Types.MEMBER
        )
        service = Service.objects.create(domain='d', description='d')
        grant = UserRol.objects.create(user=self.victim, service=service)

        self.client.get(url('admin_people_membership_del', membership.id))
        self.client.get(url('admin_people_rol_del', grant.id))

        self.assertFalse(Membership.objects.exists())
        self.assertFalse(UserRol.objects.exists())

    def test_a_plain_user_can_delete_a_rol_a_service_and_an_import(self):
        rol = Rol.objects.create(name='Operator')
        service = Service.objects.create(domain='d', description='d')
        upload = File_datas.objects.create(file_name='rows.xlsx')

        self.client.get(url('admin_rol_del', rol.id))
        self.client.get(url('admin_service_del', service.id))
        self.client.get(url('admin_import_del', upload.id))

        self.assertFalse(Rol.objects.exists())
        self.assertFalse(Service.objects.exists())
        self.assertFalse(File_datas.objects.exists())

    def test_a_plain_user_can_delete_a_pdf_template(self):
        template = VCTemplatePdf.objects.create(
            name='card', data=SimpleUploadedFile('c.html', b'<p>x</p>')
        )
        self.client.get(url('admin_template_pdf_del', template.id))

        self.assertFalse(VCTemplatePdf.objects.exists())

    def test_the_only_thing_the_check_does_is_add_a_message(self):
        # check_valid_user() calls messages.error() before returning True, so
        # the bypassed action succeeds *and* the user is told they are not
        # authorised. The message is the only trace left.
        response = self.client.get(
            url('admin_people_delete', self.victim.id), follow=True
        )

        self.assertFalse(User.objects.filter(pk=self.victim.pk).exists())
        self.assertIn(
            'User is not authorized to see admin pages',
            ' '.join(str(message) for message in response.context['messages']),
        )


class UserObjectIsolationTest(IdHubTestCase):
    """One user's wallet against another's, on the user pages."""

    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema('membership-card.json')
        self.other = factories.make_user('other@example.org', 'otherpass12')
        self.other.set_encrypted_sensitive_data()
        self.other.save()
        self.their_did = factories.make_did(label='Theirs', user=self.other)
        self.their_credential = factories.make_credential(
            self.other, self.schema, factories.make_did(label='Issuer')
        )
        self.user_login()

    def test_the_pages_that_filter_by_owner_answer_not_found(self):
        for name in ('user_credential', 'user_credential_json',
                     'user_credential_html'):
            with self.subTest(url=name):
                response = self.client.get(
                    url(name, self.their_credential.id)
                )
                self.assertEqual(response.status_code, 404)

    def test_editing_someone_elses_did_is_not_found_either(self):
        self.assertEqual(
            self.client.get(url('user_dids_edit', self.their_did.id)).status_code,
            404,
        )

    def test_but_deleting_it_works(self):
        # DidDeleteView looks the row up by pk alone, unlike the edit view
        # right above it, so any logged-in user can delete any did -- a
        # user's wallet key or an organisation's issuing key alike.
        self.client.get(url('user_dids_del', self.their_did.id))

        self.assertFalse(DID.objects.filter(pk=self.their_did.pk).exists())

    def test_the_deletion_is_logged_against_the_wrong_person(self):
        # set_EV_DID_DELETED builds the event from the row, so the owner is
        # told they deleted a did they never touched and the person who did
        # leaves no trace.
        self.client.get(url('user_dids_del', self.their_did.id))
        event = Event.objects.filter(type=Event.Types.EV_DID_DELETED).first()

        self.assertEqual(event.user, self.other)

    def test_presenting_someone_elses_credential_to_the_dlt_is_allowed(self):
        # CallOracleView does not filter by user either. The presentation
        # itself fails without a dlt, but the attempt is recorded.
        self.client.get(url('call_oracle', self.their_credential.id))

        self.assertTrue(
            Event.objects.filter(type=Event.Types.EV_USR_CRED_TO_DLT).exists()
        )


class AdminCredentialActionsTest(IdHubTestCase):
    """What the admin credential actions do once they are reached."""

    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema('membership-card.json')
        self.credential = factories.make_credential(
            self.user, self.schema, factories.make_did(label='Issuer'),
            status=VerificableCredential.Status.ISSUED,
        )
        self.admin_login()

    def test_revoking_records_one_event_for_each_side(self):
        self.client.get(url('admin_credentials_revoke', self.credential.id))
        self.credential.refresh_from_db()

        self.assertEqual(
            self.credential.status, VerificableCredential.Status.REVOKED
        )
        self.assertEqual(
            sorted(Event.objects.values_list('type', flat=True)),
            sorted([Event.Types.EV_CREDENTIAL_REVOKED_BY_ADMIN,
                    Event.Types.EV_CREDENTIAL_REVOKED]),
        )

    def test_a_credential_that_was_never_issued_is_left_alone(self):
        self.credential.status = VerificableCredential.Status.ENABLED
        self.credential.save()
        self.client.get(url('admin_credentials_revoke', self.credential.id))
        self.credential.refresh_from_db()

        self.assertEqual(
            self.credential.status, VerificableCredential.Status.ENABLED
        )
        self.assertFalse(Event.objects.exists())

    def test_revoking_twice_does_not_add_a_second_pair_of_events(self):
        for _ in range(2):
            self.client.get(url('admin_credentials_revoke', self.credential.id))

        self.assertEqual(Event.objects.count(), 2)

    def test_deleting_logs_the_credential_after_it_is_already_gone(self):
        # DeleteCredentialsView calls delete() and only then builds the two
        # events from self.object, whose primary key is None by that point.
        self.client.get(url('admin_credentials_delete', self.credential.id))

        self.assertFalse(VerificableCredential.objects.exists())
        self.assertEqual(Event.objects.count(), 2)


class EncryptionKeyAccessTest(IdHubTestCase):
    def test_with_the_key_in_place_the_form_is_not_offered_again(self):
        self.admin_login()
        response = self.client.get(reverse('idhub:encryption_key'))

        self.assertEqual(response['Location'], reverse('idhub:admin_dashboard'))

    def test_without_the_key_the_admin_is_asked_for_it(self):
        cache.set('KEY_DIDS', None)
        self.admin_login()
        response = self.client.get(reverse('idhub:encryption_key'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)

    def test_a_plain_user_is_sent_to_the_admin_dashboard(self):
        # The get() override redirects before AdminView gets to run its
        # check, so the one case it handles is also the one case where a
        # plain user is pointed at an admin page instead of their own. The
        # dashboard bounces them back, so nothing leaks.
        self.user_login()
        response = self.client.get(reverse('idhub:encryption_key'))

        self.assertEqual(response['Location'], reverse('idhub:admin_dashboard'))

    def test_without_the_key_a_plain_user_is_bounced_normally(self):
        cache.set('KEY_DIDS', None)
        self.user_login()
        response = self.client.get(reverse('idhub:encryption_key'))

        self.assertEqual(response['Location'], reverse('idhub:user_dashboard'))


class GdprTest(IdHubTestCase):
    """The branch every other test case skips by accepting the terms."""

    def setUp(self):
        super().setUp()
        self.user.accept_gdpr = False
        self.user.save()
        self.admin_user.accept_gdpr = False
        self.admin_user.save()

    def test_a_user_who_has_not_accepted_is_sent_to_the_terms(self):
        self.user_login()
        response = self.client.get(reverse('idhub:user_profile'))

        self.assertEqual(
            response['Location'], reverse('idhub:user_terms_and_conditions')
        )

    def test_an_admin_who_has_not_accepted_gets_the_admin_terms(self):
        self.admin_login()
        response = self.client.get(reverse('idhub:admin_people_list'))

        self.assertEqual(
            response['Location'], reverse('idhub:admin_terms_and_conditions')
        )

    def test_the_pages_needed_to_accept_are_not_redirected(self):
        self.user_login()
        for name in ('user_terms_and_conditions', 'user_gdpr'):
            with self.subTest(url=name):
                response = self.client.get(reverse('idhub:{}'.format(name)))
                self.assertEqual(response.status_code, 200)

    def test_the_check_runs_after_the_view_has_already_answered(self):
        # UserView.get calls super().get() first and only then check_gdpr(),
        # so the view body runs in full before the redirect is returned. For a
        # view with side effects that means they happen anyway.
        self.user_login()
        response = self.client.get(reverse('idhub:user_dids_new'))

        self.assertEqual(
            response['Location'], reverse('idhub:user_terms_and_conditions')
        )
