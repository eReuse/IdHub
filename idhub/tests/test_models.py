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

    # Add more tests for other model methods and properties
