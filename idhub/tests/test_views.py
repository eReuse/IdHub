from django.test import TestCase, RequestFactory
from django.urls import reverse

from idhub_auth.models import User
from idhub.models import Event
from idhub.admin.views import PeopleListView


class AdminDashboardViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='normaluser@example.org',
            password='testpass12',
        )
        self.user.accept_gdpr=True
        self.user.save()

        self.admin_user = User.objects.create_superuser(
                email='adminuser@example.org',
                password='adminpass12')
        self.admin_user.accept_gdpr=True
        self.admin_user.save()

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/admin/dashboard/', follow=True)

        self.assertEqual(response.status_code, 200)

    def test_view_redirects_to_login_when_not_authenticated(self):
        response = self.client.get(reverse("idhub:admin_dashboard"),
                                   follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login.html')

    def test_view_redirects_on_incorrect_login_attempt(self):
        self.client.login(email='adminuser@example.org', password='wrongpass')
        response = self.client.get(reverse('idhub:admin_dashboard'))

        self.assertEqual(response.status_code, 302)

    def test_view_redirects_to_login_on_incorrect_login_attempt(self):
        self.client.login(email='adminuser@example.org', password='wrongpass')
        response = self.client.get(reverse('idhub:admin_dashboard'),
                                   follow=True)

        self.assertTemplateUsed(response, 'auth/login.html')

    def test_login_admin_user(self):
        self.client.login(email='adminuser@example.org',
                          password='adminpass12')
        response = self.client.get(reverse('idhub:admin_dashboard'))

        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(email='adminuser@example.org',
                          password='adminpass12')
        response = self.client.get(reverse('idhub:admin_dashboard'))

        self.assertTemplateUsed(response, 'idhub/admin/dashboard.html')

    def test_admin_event_filtering(self):
        # Create a test admin user
        admin_user = User.objects.create_superuser(email='admin@example.org', password='test')
        self.client.login(email='admin@example.org', password='test')

        # Create test events, including some that should not be visible to admins
        Event.objects.create(type=Event.Types.EV_USR_REGISTERED, message="User registered")
        Event.objects.create(type=Event.Types.EV_USR_WELCOME, message="User welcomed")  # Should not appear

        # Fetch the dashboard view
        response = self.client.get('/admin/dashboard/')
        events = response.context['events']

        # Check that only admin-visible events are included
        self.assertIn(Event.Types.EV_USR_REGISTERED, [event.type for event in events])
        self.assertNotIn(Event.Types.EV_USR_WELCOME, [event.type for event in events])

    def test_access_control(self):
        # Attempt to access the dashboard as a non-admin user
        regular_user = User.objects.create_user(email='user', password='test')
        self.client.login(email='user@example.org', password='test')
        response = self.client.get('/admin/dashboard/')
        self.assertEqual(response.status_code, 302)  # Or 403 if not redirected

        # Access as an admin
        admin_user = User.objects.create_superuser(email='admin@example.org', password='test')
        self.client.login(email='admin@example.org', password='test')
        response = self.client.get('/admin/dashboard/')
        self.assertEqual(response.status_code, 200)


class PeopleListViewTest(TestCase):

    def setUp(self):
        # Set up a RequestFactory to create mock requests
        self.factory = RequestFactory()

        # Create some user instances for testing
        self.user = User.objects.create_user(email='normaluser@example.org',
                                             password='testpass12')
        self.user.accept_gdpr=True
        self.user.save()
        self.admin_user = User.objects.create_superuser(
                email='adminuser@example.org',
                password='adminpass12')
        self.admin_user.accept_gdpr=True
        self.admin_user.save()

        # Create a request object for the view
        self.request = self.factory.get(reverse('idhub:admin_people_list'))

        self.request.user = self.admin_user
        self.client.login(email='adminuser@example.org', password='adminpass12')
        self.request.session = self.client.session

    def test_template_used(self):
        response = PeopleListView.as_view()(self.request)

        self.assertEqual(response.template_name[0], "idhub/admin/people.html")

    def test_context_data(self):
        response = PeopleListView.as_view()(self.request)

        self.assertIn('users', response.context_data)

        # Assuming 2 users were created
        self.assertEqual(len(response.context_data['users']), 2)

    def test_get_queryset(self):
        view = PeopleListView()
        view.setup(self.request)
        queryset = view.get_queryset()

        # Assuming 2 users in the database
        self.assertEqual(queryset.count(), 2)


class UserDashboardViewTests(TestCase):
    def setUp(self):
        # Create test users
        self.admin_user = User.objects.create_superuser('admin@example.org', 'password')
        self.admin_user.accept_gdpr=True
        self.admin_user.save()
        self.regular_user = User.objects.create_user('regular@example.org', 'password')
        self.regular_user.accept_gdpr=True
        self.regular_user.save()
        
        # Create events visible to users
        self.visible_events_types = [
            Event.Types.EV_USR_WELCOME,
            Event.Types.EV_USR_UPDATED,
            Event.Types.EV_DID_CREATED,
            Event.Types.EV_DID_DELETED,
            Event.Types.EV_CREDENTIAL_DELETED,
            Event.Types.EV_CREDENTIAL_ISSUED,
            Event.Types.EV_CREDENTIAL_PRESENTED,
            Event.Types.EV_CREDENTIAL_CAN_BE_REQUESTED,
            Event.Types.EV_CREDENTIAL_REVOKED,
        ]
        
        # Create events for both users
        for event_type in self.visible_events_types:
            Event.objects.create(type=event_type, message=f"Test event for {event_type.label}", user=self.regular_user)
        
        # Create an event that should not be visible to a regular user
        Event.objects.create(type=Event.Types.EV_USR_REGISTERED, message="Admin only event", user=self.regular_user)

    def test_events_visibility_for_regular_user(self):
        self.client.login(email='regularuser@example.org', password='password')
        response = self.client.get(reverse('idhub:user_dashboard'))
        # Ensure the response contains only the events that should be visible
        for event in Event.objects.filter(user=self.regular_user, type__in=self.visible_events_types):
            self.assertContains(response, event.message)
        # Ensure the response does not contain the admin only event
        self.assertNotContains(response, "Admin only event")

    def test_no_events_for_regular_user(self):
        # Delete all events for the setup user
        Event.objects.filter(user=self.regular_user).delete()
        self.client.login(email='regularuser@example.org', password='password')
        response = self.client.get(reverse('idhub:user_dashboard'))
        # Verify that the response indicates no events are available
        self.assertContains(response, "No events available")  # Adjust based on your actual no-events message

    def test_events_visibility_for_new_user(self):
        # Create a new user who has no events
        new_user = User.objects.create_user('new@example.org', 'password')
        self.client.login(email='newuser@example.org', password='password')
        response = self.client.get(reverse('idhub:user_dashboard'))
        # Verify that the response correctly indicates no events for the new user
        self.assertContains(response, "No events available")  # Adjust based on your actual no-events message

    def test_unauthorized_access(self):
        # Attempt to access the dashboard without logging in
        response = self.client.get(reverse('idhub:user_dashboard'), follow=True)
        # Ensure the response redirects to the login page
        self.assertTemplateUsed(response, 'auth/login.html')
