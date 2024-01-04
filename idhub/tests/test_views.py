from django.urls import reverse
from django.test import TestCase, RequestFactory

from idhub_auth.models import User
from idhub.admin.views import PeopleListView


class AdminDashboardViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email='normaluser@example.org',
                                             password='testpass12')
        self.admin_user = User.objects.create_superuser(
                email='adminuser@example.org',
                password='adminpass12')

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


class PeopleListViewTest(TestCase):

    def setUp(self):
        # Set up a RequestFactory to create mock requests
        self.factory = RequestFactory()

        # Create some user instances for testing
        self.user = User.objects.create_user(email='normaluser@example.org',
                                             password='testpass12')
        self.admin_user = User.objects.create_superuser(
                email='adminuser@example.org',
                password='adminpass12')

        # Create a request object for the view
        self.request = self.factory.get(reverse('idhub:admin_people_list'))

        self.request.user = self.admin_user

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
