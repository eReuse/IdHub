from django.db.utils import IntegrityError
from django.test import TestCase

from idhub.models import Event, File_datas, Membership, Rol, UserRol, Service
from idhub_auth.models import User
from test_support.base import IdHubBaseTestCase


class EventModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(email='testuser@example.org')
        Event.objects.create(message='Test Event', type=1, user=user)

    def test_event_creation(self):
        event = Event.objects.get(message='Test Event')
        self.assertEqual(event.message, 'Test Event')
        self.assertEqual(event.get_type_name(), 'User registered')


class UserTest(TestCase):
    """
    Tests the very basic aspects of the User model,
    like field properties and methods behaving as expected.
    Further testing is recommended.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="test@example.com",
            is_admin=True,
            first_name="Dummy",
            last_name="Dummyson"
        )

    def test_field_properties(self):
        user = User.objects.get(email="test@example.com")
        self.assertEqual(user._meta.get_field('email').max_length, 255)
        self.assertTrue(user._meta.get_field('email').unique)
        self.assertTrue(user._meta.get_field('is_active').default)
        self.assertFalse(user._meta.get_field('is_admin').default)

    def test_string_representation(self):
        self.assertEqual(str(self.user), "test@example.com")

    def test_has_perm(self):
        self.assertTrue(self.user.has_perm(None))

    def test_has_module_perms(self):
        self.assertTrue(self.user.has_module_perms(None))

    def test_is_staff_property(self):
        self.assertTrue(self.user.is_staff)

    def test_username_property(self):
        self.assertEqual(self.user.username, self.user.email)

    def test_get_memberships(self):
        Membership.objects.create(user=self.user,
                                  type=Membership.Types.BENEFICIARY)
        Membership.objects.create(user=self.user,
                                  type=Membership.Types.EMPLOYEE)

        # Compared as a set: get_memberships() joins a set, so the order is
        # non-deterministic. Labels are taken from the choices because they
        # are translated and depend on LANGUAGE_CODE.
        labels = dict(Membership.Types.choices)
        self.assertEqual(
            set(self.user.get_memberships().split(", ")),
            {str(labels[Membership.Types.BENEFICIARY]),
             str(labels[Membership.Types.EMPLOYEE])}
        )

    def test_get_memberships_without_any(self):
        self.assertEqual(self.user.get_memberships(), "")

    def test_get_roles(self):
        user = User.objects.get(email="test@example.com")
        service = Service.objects.create(domain="Test Service")
        role1 = Rol.objects.create(name="Role 1")
        role2 = Rol.objects.create(name="Role 2")
        service.rol.add(role1, role2)
        UserRol.objects.create(user=user, service=service)

        # Compared as a set: get_roles() joins a set, so the order is
        # non-deterministic
        self.assertEqual(set(user.get_roles().split(", ")),
                         {"Role 1", "Role 2"})

    def test_get_roles_without_any(self):
        self.assertEqual(self.user.get_roles(), "")


class UserManagerTest(TestCase):
    def test_create_user_normalizes_the_email_domain(self):
        user = User.objects.create_user(email="Mixed@EXAMPLE.ORG")
        self.assertEqual(user.email, "Mixed@example.org")

    def test_create_user_requires_an_email(self):
        for email in ("", None):
            with self.subTest(email=email):
                with self.assertRaises(ValueError):
                    User.objects.create_user(email=email)

    def test_create_user_is_not_an_admin(self):
        user = User.objects.create_user(email="plain@example.org", password="pw")
        self.assertFalse(user.is_admin)
        self.assertTrue(user.check_password("pw"))

    def test_create_user_without_password_is_unusable(self):
        user = User.objects.create_user(email="nopw@example.org")
        self.assertFalse(user.has_usable_password())

    def test_create_superuser_is_an_admin(self):
        user = User.objects.create_superuser(email="root@example.org")
        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_staff)


class MembershipTest(IdHubBaseTestCase):
    def test_get_type_is_the_label_of_every_type(self):
        for type in Membership.Types:
            with self.subTest(type=type.name):
                membership = Membership(type=type.value)
                self.assertEqual(membership.get_type(), type.label)

    def test_get_type_of_a_value_outside_the_enum(self):
        # dict.get, not Types(), so an unknown value is None instead of an
        # error. Nothing downstream checks for it.
        self.assertIsNone(Membership(type=99).get_type())

    def test_the_dates_are_optional(self):
        membership = Membership.objects.create(
            type=Membership.Types.MEMBER, user=self.make_user()
        )
        self.assertIsNone(membership.start_date)
        self.assertIsNone(membership.end_date)

    def make_user(self):
        return User.objects.create_user(email='member@example.org')


class RolTest(IdHubBaseTestCase):
    def test_string_representation_is_the_name(self):
        self.assertEqual(str(Rol(name='Reader')), 'Reader')

    def test_the_description_is_optional(self):
        rol = Rol.objects.create(name='Reader')
        self.assertIsNone(rol.description)


class ServiceTest(IdHubBaseTestCase):
    def setUp(self):
        super().setUp()
        self.service = Service.objects.create(
            domain='verifier.example.org', description='A verifier'
        )

    def test_get_roles_is_sorted_by_name(self):
        for name in ('Writer', 'Admin', 'Reader'):
            self.service.rol.add(Rol.objects.create(name=name))
        self.assertEqual(self.service.get_roles(), 'Admin, Reader, Writer')

    def test_get_roles_without_any_role(self):
        # A translated literal, not an empty string, because it is rendered
        # straight into the admin tables.
        self.assertEqual(self.service.get_roles(), 'None')

    def test_string_representation_includes_the_roles(self):
        self.service.rol.add(Rol.objects.create(name='Reader'))
        self.assertEqual(str(self.service), 'verifier.example.org -> Reader')


class UserRolTest(IdHubBaseTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email='holder@example.org')
        self.service = Service.objects.create(domain='s.example.org', description='s')

    def test_a_user_can_only_be_granted_a_service_once(self):
        UserRol.objects.create(user=self.user, service=self.service)
        with self.assertRaises(IntegrityError):
            UserRol.objects.create(user=self.user, service=self.service)

    def test_the_same_service_can_be_granted_to_another_user(self):
        other = User.objects.create_user(email='other@example.org')
        UserRol.objects.create(user=self.user, service=self.service)
        UserRol.objects.create(user=other, service=self.service)
        self.assertEqual(self.service.users.count(), 2)


class FileDatasTest(IdHubBaseTestCase):
    def test_an_import_is_recorded_as_successful_by_default(self):
        record = File_datas.objects.create(file_name='users.csv')
        self.assertTrue(record.success)
        self.assertIsNotNone(record.created_at)
