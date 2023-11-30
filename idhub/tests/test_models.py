from django.test import TestCase
from idhub.models import Event
from idhub_auth.models import User


class EventModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(email='testuser@example.org')
        Event.objects.create(message='Test Event', type=1, user=user)

    def test_event_creation(self):
        event = Event.objects.get(id=1)
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

    def test_get_memberships(self):
        # TODO
        pass

    def test_get_roles(self):
        # TODO
        pass
