from django.urls import reverse

from test_support.base import IdHubTestCase


class TemplateTest(IdHubTestCase):

    def test_dashboard_template(self):
        self.admin_login()
        response = self.client.get(reverse('idhub:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'idhub/base_admin.html')
