from django.urls import reverse
from django.test import Client, TestCase

from idhub_auth.models import User


class TemplateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
                email='adminuser@example.org',
                password='adminpass12')

    def test_dashboard_template(self):
        self.client.login(email='adminuser@example.org', password='adminpass12')
        response = self.client.get(reverse('idhub:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'idhub/base_admin.html')
