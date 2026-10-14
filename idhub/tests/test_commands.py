"""The management commands, which are how a deployment is bootstrapped.

``docker/idhub.entrypoint.sh`` decides which ones run:

* a new deployment without demo data: ``init_org`` and then ``init_admin``;
* a new deployment with ``DEMO=true``: ``demo_data`` (and ``demo_data_dpp``);
* an existing deployment: ``send_mail_admins``, to ask the admins to re-enter
  the vault password;
* ``DEMO_AUTODECRYPT=true``: ``open_service``, which unlocks the vault and
  starts the server.

So a command that crashes takes the whole container with it, and that is what
most of these tests are about. Every one of them pins the settings it talks
about: the commands read ``INIT_ADMIN_*``, ``OIDC_ORGS``,
``CREATE_TEST_USERS`` and ``DEMO_CREATE_SCHEMAS`` straight from the
environment.
"""
import json

from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import override_settings

from idhub.management.commands import demo_data, init_org
from idhub.models import DID, Event, Rol, Schemas, Service, UserRol
from idhub_auth.models import User
from oidc4vp.models import Organization
from test_support import factories
from test_support.base import IdHubBaseTestCase, IdHubTestCase


def run(command, *args, **options):
    """Calls a command with its output captured, and hands it back."""
    out = StringIO()
    call_command(command, *args, stdout=out, stderr=out, **options)
    return out.getvalue()


class InitOrgTest(IdHubBaseTestCase):
    """``init_org <name>``: the row that says "this instance is us"."""

    def test_the_organization_is_created_as_the_main_one(self):
        run('init_org', 'Example Org')

        org = Organization.objects.get()
        self.assertEqual(org.name, 'Example Org')
        # Compared against the command's own attribute, not settings.DOMAIN:
        # every command copies the setting into a class attribute at import
        # time, so what a test overrides afterwards never reaches them.
        self.assertEqual(org.domain, init_org.Command.DOMAIN)
        self.assertTrue(org.main)

    def test_the_name_is_optional_and_defaults_to_empty(self):
        run('init_org')

        self.assertEqual(Organization.objects.get().name, '')

    def test_the_credentials_the_peers_will_use_are_generated(self):
        run('init_org', 'First')
        run('init_org', 'Second')

        first, second = Organization.objects.all()
        self.assertEqual(len(first.client_id), 24)
        self.assertNotEqual(first.client_id, second.client_id)
        self.assertNotEqual(first.client_secret, second.client_secret)

    def test_running_it_twice_leaves_two_main_organizations(self):
        # Nothing checks for an existing row, and get_org() takes the first
        # main one it finds, so a second run silently decides which identity
        # the instance has.
        run('init_org', 'First')
        run('init_org', 'Second')

        self.assertEqual(Organization.objects.filter(main=True).count(), 2)

    def test_the_organization_vault_is_left_unencrypted(self):
        # demo_data does call set_encrypted_sensitive_data() on the row it
        # creates; this command does not, so the two bootstrap paths leave the
        # instance in different states. The vault is created later, lazily, by
        # the first DID (see DID.set_key_material).
        run('init_org', 'Example Org')

        org = Organization.objects.get()
        self.assertFalse(org.encrypted_sensitive_data)
        self.assertFalse(org.salt)


class InitAdminTest(IdHubBaseTestCase):
    """``init_admin <email> <password>``: the first account."""

    # The command encrypts the vault with whatever key the cache holds, and it
    # never puts one there itself. 'DEMO' is the value demo_data hardcodes, so
    # it is also the one a real deployment ends up with.
    KEY_DIDS = 'DEMO'

    def test_the_admin_is_created_with_an_encrypted_vault(self):
        run('init_admin', 'admin@example.org', 'adminpass12')

        admin = User.objects.get()
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.check_password('adminpass12'))
        self.assertTrue(admin.encrypted_sensitive_data)
        self.assertTrue(admin.salt)

    def test_the_vault_is_readable_with_the_key_that_was_in_the_cache(self):
        run('init_admin', 'admin@example.org', 'adminpass12')

        admin = User.objects.get()
        self.assertTrue(admin.decrypt_sensitive_data())

    def test_without_the_key_in_the_cache_the_command_crashes(self):
        # derive_key_from_password() does cache.get("KEY_DIDS").encode(), and
        # in a fresh deployment nothing has put it there: the entrypoint runs
        # init_admin before anybody has unlocked the vault, and the cache is
        # per process anyway.
        cache.delete('KEY_DIDS')

        with self.assertRaises(AttributeError):
            run('init_admin', 'admin@example.org', 'adminpass12')

    def test_the_user_survives_the_crash_without_a_vault(self):
        cache.delete('KEY_DIDS')
        with self.assertRaises(AttributeError):
            run('init_admin', 'admin@example.org', 'adminpass12')

        admin = User.objects.get()
        self.assertTrue(admin.is_admin)
        self.assertEqual(admin.encrypted_sensitive_data, '')

    def test_running_it_twice_is_an_integrity_error(self):
        run('init_admin', 'admin@example.org', 'adminpass12')

        with self.assertRaises(IntegrityError):
            run('init_admin', 'admin@example.org', 'adminpass12')

    def test_both_arguments_are_required(self):
        for args in ((), ('admin@example.org',)):
            with self.subTest(args=args):
                with self.assertRaises(CommandError):
                    run('init_admin', *args)


class SendMailAdminsTest(IdHubTestCase):
    """``send_mail_admins``: run on every redeploy, before anything else."""

    @override_settings(ENABLE_EMAIL=True)
    def test_every_admin_is_written_to_and_nobody_else(self):
        factories.make_user('second@example.org', 'secondpass12', admin=True)

        run('send_mail_admins')

        self.assertEqual(
            sorted(sum((m.to for m in mail.outbox), [])),
            [self.ADMIN_EMAIL, 'second@example.org'],
        )

    @override_settings(ENABLE_EMAIL=True)
    def test_the_mail_carries_the_domain_in_both_bodies(self):
        run('send_mail_admins')

        message, = mail.outbox
        self.assertNotIn('\n', message.subject)
        self.assertIn(settings.DOMAIN, message.body)
        html, content_type = message.alternatives[0]
        self.assertEqual(content_type, 'text/html')
        self.assertIn('https://{}/'.format(settings.DOMAIN), html)

    @override_settings(ENABLE_EMAIL=False)
    def test_with_email_disabled_the_body_is_only_logged(self):
        logger = 'idhub.management.commands.send_mail_admins'
        with self.assertLogs(logger, level='WARNING') as logs:
            run('send_mail_admins')

        self.assertEqual(mail.outbox, [])
        self.assertIn(self.ADMIN_EMAIL, logs.output[0])

    @override_settings(ENABLE_EMAIL=True)
    def test_a_broken_mail_server_does_not_stop_the_deployment(self):
        # The command is the last thing between the entrypoint and runserver,
        # so swallowing the error is deliberate: the error goes to the log and
        # the container comes up.
        logger = 'idhub.management.commands.send_mail_admins'
        with patch(
            'idhub.management.commands.send_mail_admins'
            '.EmailMultiAlternatives.send',
            side_effect=OSError('no smtp here'),
        ), self.assertLogs(logger, level='ERROR') as logs:
            run('send_mail_admins')

        self.assertIn('no smtp here', logs.output[0])

    @override_settings(ENABLE_EMAIL=True)
    def test_an_instance_without_admins_sends_nothing(self):
        User.objects.update(is_admin=False)

        run('send_mail_admins')

        self.assertEqual(mail.outbox, [])


class OpenServiceTest(IdHubTestCase):
    """``open_service <key> <ip:port>``: unlock the vault and serve.

    ``call_command('runserver')`` is patched everywhere: the point of the
    tests is which paths reach it, not the server.
    """

    def setUp(self):
        super().setUp()
        patcher = patch('idhub.management.commands.open_service.call_command')
        self.runserver = patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(cache.delete, 'KEY_DIDS')

    def test_the_key_is_published_and_the_server_started(self):
        run('open_service', 'the-key', '0.0.0.0:8000')

        self.assertEqual(cache.get('KEY_DIDS'), 'the-key')
        self.runserver.assert_called_once_with('runserver', '0.0.0.0:8000')

    def test_with_no_dids_the_key_is_taken_on_trust(self):
        # There is nothing to decrypt yet, so any key is accepted and becomes
        # the one the first DID will be encrypted with.
        run('open_service', 'anything-goes', '0.0.0.0:8000')

        self.assertFalse(DID.objects.exists())
        self.assertEqual(cache.get('KEY_DIDS'), 'anything-goes')
        self.runserver.assert_called_once()

    def test_an_existing_did_is_used_to_check_the_key(self):
        factories.make_did(label='Existing')

        run('open_service', self.KEY_DIDS, '0.0.0.0:8000')

        self.runserver.assert_called_once()

    def test_a_wrong_key_stops_the_service_instead_of_serving_garbage(self):
        factories.make_did(label='Existing')
        logger = 'idhub.management.commands.open_service'

        with self.assertLogs(logger, level='ERROR') as logs:
            run('open_service', 'not-the-key', '0.0.0.0:8000')

        self.assertIn('Key no valid!', logs.output[0])
        self.runserver.assert_not_called()
        self.assertIsNone(cache.get('KEY_DIDS'))

    def test_the_command_accepts_the_gdpr_on_behalf_of_the_admin(self):
        # A side effect nothing in the name suggests: whoever starts the
        # service in demo mode ticks the first admin's consent box for them.
        self.admin_user.accept_gdpr = False
        self.admin_user.save()

        run('open_service', self.KEY_DIDS, '0.0.0.0:8000')

        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.accept_gdpr)

    def test_an_instance_without_an_admin_crashes(self):
        # filter(...).first() can be None and the next line writes to it.
        # Same shape as the webhook endpoints of §6.
        User.objects.update(is_admin=False)

        with self.assertRaises(AttributeError):
            run('open_service', self.KEY_DIDS, '0.0.0.0:8000')

    def test_both_arguments_are_optional(self):
        run('open_service')

        self.assertEqual(cache.get('KEY_DIDS'), '')
        self.runserver.assert_called_once_with('runserver', '')


@override_settings(
    CREATE_TEST_USERS=False,
    DEMO_CREATE_SCHEMAS=False,
    INIT_ADMIN_EMAIL='admin@example.org',
    INIT_ADMIN_PASSWORD='1234',
)
# OIDC_ORGS is a class attribute of the command, read at import time, so
# override_settings cannot reach it: without this patch the tests would load
# whatever CSV of peer organizations the developer's .env points at.
@patch.object(demo_data.Command, 'OIDC_ORGS', '')
class DemoDataTest(IdHubBaseTestCase):
    """``demo_data``: the whole bootstrap of a demo deployment in one call."""

    def setUp(self):
        super().setUp()
        self.addCleanup(cache.delete, 'KEY_DIDS')

    def test_the_vault_password_of_a_demo_is_hardcoded(self):
        run('demo_data')

        self.assertEqual(cache.get('KEY_DIDS'), 'DEMO')

    def test_the_organization_and_the_admin_are_created_encrypted(self):
        run('demo_data')

        org = Organization.objects.get()
        domain = demo_data.Command.DOMAIN
        self.assertEqual((org.name, org.domain, org.main), (domain, domain, True))
        self.assertTrue(org.encrypted_sensitive_data)

        admin = User.objects.get()
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.check_password('1234'))
        self.assertTrue(admin.decrypt_sensitive_data())

    def test_the_demo_did_comes_from_the_example_key_material(self):
        run('demo_data')

        did = DID.objects.get()
        self.assertEqual(did.label, 'DEMO')
        self.assertEqual(did.type, DID.Types.WEB)
        self.assertIsNone(did.user)
        self.assertIn('Ed25519', did.get_key_material())

    def test_the_did_is_a_did_web_pointing_at_this_instance(self):
        run('demo_data')

        # Here the live setting is the right reference, not the command's
        # frozen copy: the domain of the DID is written by DID.set_did(), which
        # reads settings.DOMAIN when it runs.
        self.assertTrue(
            DID.objects.get().did.startswith('did:web:' + settings.DOMAIN)
        )

    @override_settings(CREATE_TEST_USERS=True)
    def test_the_five_test_users_each_get_a_did(self):
        run('demo_data')

        users = User.objects.filter(email__startswith='user').order_by('email')
        self.assertEqual(
            [u.email for u in users],
            ['user{}@example.org'.format(n) for n in range(1, 6)],
        )
        self.assertEqual(DID.objects.filter(user__isnull=False).count(), 5)

    @override_settings(CREATE_TEST_USERS=True)
    def test_a_test_user_gets_a_vault_without_anybody_asking_for_one(self):
        # create_users() never calls set_encrypted_sensitive_data(); the vault
        # appears because DID.set_key_material() creates it on the fly for
        # whoever owns the DID. And it is encrypted with KEY_DIDS, the
        # instance-wide key, not with the user's password.
        run('demo_data')

        user = User.objects.get(email='user1@example.org')
        self.assertTrue(user.check_password('1234'))
        self.assertTrue(user.encrypted_sensitive_data)
        self.assertTrue(user.dids.get().get_key_material())

    @override_settings(DEMO_CREATE_SCHEMAS=True)
    def test_the_schemas_shipped_in_the_repo_are_loaded(self):
        run('demo_data')

        self.assertTrue(Schemas.objects.exists())
        self.assertTrue(
            Schemas.objects.filter(file_schema='membership-card.json').exists()
        )

    @override_settings(DEMO_CREATE_SCHEMAS=True)
    def test_the_schemas_already_loaded_are_left_alone(self):
        # The schema loop is the only idempotent part of the command.
        factories.make_schemas()

        run('demo_data')

        loaded = list(Schemas.objects.values_list('file_schema', flat=True))
        self.assertEqual(len(loaded), len(set(loaded)))

    @override_settings(DEMO_CREATE_SCHEMAS=True)
    def test_a_json_file_that_is_not_a_schema_is_loaded_anyway(self):
        # os.listdir() is not filtered by extension, so a leftover backup
        # loads as one more schema: there is one in the working tree right
        # now, schemas/course-credential.json-bk, and a demo deployment offers
        # it in the admin pages like any other.
        directory = self.write_schemas_dir('backup.json-bk', '{"title": "Copy"}')

        with override_settings(SCHEMAS_DIR=directory):
            run('demo_data')

        self.assertEqual(
            sorted(Schemas.objects.values_list('file_schema', flat=True)),
            ['backup.json-bk', 'membership-card.json'],
        )

    @override_settings(DEMO_CREATE_SCHEMAS=True)
    def test_a_file_that_is_not_json_at_all_aborts_the_whole_bootstrap(self):
        # _create_schemas() does catch the parse error, but SchemaManager
        # .create() parses `data` again to walk allOf, and that one is
        # unguarded: an editor swap file or a README in schemas/ stops the
        # container from coming up, after the admin and the DID are already
        # created.
        directory = self.write_schemas_dir('notes.txt', 'remember to delete me')

        with override_settings(SCHEMAS_DIR=directory):
            with self.assertRaises(json.JSONDecodeError):
                run('demo_data')

    def write_schemas_dir(self, name, content):
        import tempfile
        from pathlib import Path

        directory = Path(tempfile.mkdtemp(prefix='idhub-test-schemas-'))
        directory.joinpath('membership-card.json').write_text(
            factories.read_schema('membership-card.json')
        )
        directory.joinpath(name).write_text(content)
        return str(directory)

    def test_a_second_run_cannot_even_get_past_the_organization(self):
        # So a demo deployment is not re-runnable: the admin email is unique
        # and the command creates it unconditionally.
        run('demo_data')

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                run('demo_data')

        self.assertEqual(User.objects.count(), 1)

    def test_a_predefined_token_is_registered_for_the_webhook(self):
        token = 'b2b8e0a9-dc1f-4d19-8e9e-f4a3a7f0e111'

        run('demo_data', token)

        from webhook.models import Token
        self.assertTrue(Token.objects.filter(token=token).exists())

    def test_a_predefined_did_file_is_read_instead_of_the_example_one(self):
        key_material = json.dumps({
            'kty': 'OKP', 'crv': 'Ed25519',
            'x': 'IRqDfIumhbKKHhqMjOngikQmGoT1cZ6LPP-JjXa8CsY',
            'd': 'AZXUEnJYFbGcn3Ebzy3vQWYFzx6rdnoHKilaMYUWuHA',
            'kid': 'Generated',
        })
        path = self.write_did_file({'label': 'Imported', 'key_material': key_material})

        run('demo_data', '', path)

        self.assertEqual(DID.objects.get().label, 'Imported')

    def test_a_did_file_without_key_material_leaves_no_did(self):
        path = self.write_did_file({'label': 'Useless'})

        run('demo_data', '', path)

        self.assertFalse(DID.objects.exists())

    def test_a_did_file_that_is_not_json_leaves_no_did(self):
        # open_example_did() swallows the parse error and returns '', which is
        # falsy, so the demo ends up without an issuer DID and nothing says so.
        path = self.write_did_file('not json at all')

        run('demo_data', '', path)

        self.assertFalse(DID.objects.exists())

    def test_a_did_file_that_does_not_exist_crashes(self):
        with self.assertRaises(FileNotFoundError):
            run('demo_data', '', '/nonexistent/keys.json')

    def write_did_file(self, content):
        import tempfile
        from pathlib import Path

        path = Path(tempfile.mkdtemp()).joinpath('keys_did.json')
        path.write_text(
            content if isinstance(content, str) else json.dumps(content)
        )
        return str(path)


class DemoDataDppTest(IdHubBaseTestCase):
    """``demo_data_dpp``: the DPP extra that runs right after ``demo_data``.

    The command cannot be exercised end to end from a test: ``create_did()``
    asks for a ``WEBETH`` DID and ``DID.set_did()`` then posts to
    ``{API_DLT_URL}/registerUser``, ``handle()`` writes the operator token to
    ``/shared/$OPERATOR_TOKEN_FILE`` and the credential is handed to the
    oracle. What is pinned here is everything that happens before that first
    network call, because that is what stops a container from coming up.
    """

    def test_without_the_demo_admin_it_crashes_on_a_none(self):
        # handle() takes the admin from filter(...).first() and never looks at
        # the result, so running demo_data_dpp on a deployment that was not
        # seeded by demo_data aborts with an AttributeError and no explanation.
        with self.assertRaises(AttributeError) as caught:
            run('demo_data_dpp')

        self.assertIn('set_encrypted_sensitive_data', str(caught.exception))

    @override_settings(INIT_ADMIN_EMAIL='boss@example.org')
    def test_the_admin_address_is_hardcoded_and_ignores_the_setting(self):
        # Unlike demo_data, this one has 'admin@example.org' written into
        # handle(): a demo deployment that sets INIT_ADMIN_EMAIL to anything
        # else gets the same crash as an empty database.
        factories.make_user('boss@example.org', 'bosspass12345', admin=True)

        with self.assertRaises(AttributeError):
            run('demo_data_dpp')

    def test_the_credential_needs_the_dlt_schema_to_be_loaded(self):
        # create_credential() goes for organization-membership-dlt.json with a
        # bare get(): if DEMO_CREATE_SCHEMAS was off, or that file is not in
        # SCHEMAS_DIR, the command dies here too.
        from idhub.management.commands.demo_data_dpp import Command

        with self.assertRaises(Schemas.DoesNotExist):
            Command().create_credential()


class CreateExampleDataTest(IdHubBaseTestCase):
    """``create_example_data``: faker fixtures for manual testing."""

    def test_with_no_options_it_fills_every_table(self):
        output = run('create_example_data', '--amount', '1')

        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Rol.objects.count(), 1)
        self.assertEqual(Service.objects.count(), 1)
        self.assertEqual(UserRol.objects.count(), 1)
        self.assertIn('Created 1 Event objects', output)

    def test_the_user_roles_are_drawn_at_random_and_collide(self):
        # Each UserRol pairs a random user with a random service, and the pair
        # is unique in the database: with a small --amount the command quietly
        # creates fewer rows than asked for and only says so on stdout. Only
        # the report can be asserted on, because the IntegrityError the
        # command caught makes Django roll the atomic block back.
        with transaction.atomic():
            output = run(
                'create_example_data',
                '--users', '1', '--services', '1', '--userroles', '2',
            )

        self.assertIn("Couldn't create UserRol object.", output)
        self.assertIn('Created 1 UserRol objects', output)

    def test_a_single_table_can_be_asked_for(self):
        run('create_example_data', '--events', '3')

        self.assertEqual(Event.objects.count(), 3)
        self.assertEqual(User.objects.count(), 0)

    def test_two_options_are_both_honoured(self):
        run('create_example_data', '--events', '1', '--roles', '2')

        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Rol.objects.count(), 2)

    def test_the_generated_events_never_use_the_last_five_types(self):
        # EXISTING_EVENTS is 30 and there are 35 types, so a third of the
        # event list can never show up in the fixtures.
        run('create_example_data', '--events', '50')

        self.assertLessEqual(max(Event.objects.values_list('type', flat=True)), 30)

    def test_registering_a_user_reports_the_email(self):
        output = run('create_example_data', '--register', 'new@example.org', 'pw')

        self.assertIn('Successfully registered user: new@example.org', output)
        self.assertTrue(User.objects.get(email='new@example.org').check_password('pw'))

    def test_registering_the_same_user_twice_is_reported_and_not_raised(self):
        # The command catches the IntegrityError, which is only safe because a
        # management command runs in autocommit: the atomic() here is what a
        # TestCase needs to keep the connection usable afterwards.
        run('create_example_data', '--register', 'new@example.org', 'pw')

        with transaction.atomic():
            output = run('create_example_data', '--register', 'new@example.org', 'pw')

        self.assertIn('Failed to register user: new@example.org', output)
        self.assertEqual(User.objects.filter(email='new@example.org').count(), 1)

    def test_a_registered_superuser_is_an_admin(self):
        run('create_example_data', '--register-superuser', 'boss@example.org', 'pw')

        self.assertTrue(User.objects.get(email='boss@example.org').is_admin)

    def test_the_bulk_superusers_have_no_usable_password(self):
        run('create_example_data', '--superusers', '2')

        self.assertEqual(User.objects.filter(is_admin=True).count(), 2)
        self.assertFalse(User.objects.first().has_usable_password())

    def test_the_generated_users_have_an_empty_password_hash(self):
        # create_users() goes through Model.objects.create(), not the manager's
        # create_user(), so set_password() never runs and the column is left
        # empty. Django still calls that "usable", but nothing matches it.
        run('create_example_data', '--users', '1')

        user = User.objects.get()
        self.assertEqual(user.password, '')
        self.assertFalse(user.check_password(''))

    def test_asking_for_a_user_role_by_id_crashes(self):
        # get_or_create_user() queries User.objects.get(user_id=...), and the
        # field is called id: the --userrole option has never worked.
        user = factories.make_user('member@example.org', 'memberpass12')
        service = Service.objects.create(domain='example.org', description='d')

        with self.assertRaises(Exception) as caught:
            run('create_example_data', '--userrole', str(user.id), str(service.id))

        self.assertIn('user_id', str(caught.exception))
