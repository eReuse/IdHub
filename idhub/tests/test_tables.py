from datetime import datetime

from django.test import TestCase
from django.urls import reverse

from idhub_auth.models import User
from idhub.admin.tables import DashboardTable, UserTable
from idhub.models import Event, Membership, Rol, UserRol, Service


class AdminDashboardTableTest(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
                email='adminuser@example.org',
                password='adminpass12')

    @classmethod
    def setUpTestData(cls):
        # Creating test events with different dates
        Event.objects.create(message='Event 1', type=1,
                             created=datetime(2023, 1, 3))
        Event.objects.create(message='Event 2', type=2,
                             created=datetime(2023, 1, 2))
        Event.objects.create(message='Event 3', type=3,
                             created=datetime(2023, 1, 25))

    def test_sorting_by_date(self):
        # Create the table
        table = DashboardTable(Event.objects.all())

        # Apply sorting
        table.order_by = 'created'

        # Fetch the sorted records
        sorted_records = list(table.rows)

        # Verify the order is as expected
        self.assertTrue(sorted_records[0].record.created
                        < sorted_records[1].record.created)
        self.assertTrue(sorted_records[1].record.created
                        < sorted_records[2].record.created)

    def test_table_in_template(self):
        self.client.login(email='adminuser@example.org', password='adminpass12')
        response = self.client.get(reverse('idhub:admin_dashboard'))

        self.assertTemplateUsed(response, 'idhub/custom_table.html')

    def test_table_data(self):
        Event.objects.create(message="test_event", type=2)
        Event.objects.create(message="test_event", type=9)

        table = DashboardTable(Event.objects.all())
        self.assertTrue(isinstance(table, DashboardTable))
        self.assertEqual(len(table.rows), Event.objects.count())

    def test_table_columns(self):
        table = DashboardTable(Event.objects.all())
        expected_columns = ['type', 'message', 'created']
        for column in expected_columns:
            self.assertIn(column, table.columns)

    def test_pagination(self):
        # TODO
        pass


class UserTableTest(TestCase):

    def setUp(self):
        self.user1 = User.objects.create(email="user1@example.com")
        self.user2 = User.objects.create(email="user2@example.com")
        Membership.objects.create(user=self.user1,
                                  type=Membership.Types.BENEFICIARY)

        # Set up roles and services
        service = Service.objects.create(domain="Test Service")
        role = Rol.objects.create(name="Role 1")
        service.rol.add(role)
        UserRol.objects.create(user=self.user1, service=service)

        self.table = UserTable(User.objects.all())

    def test_membership_column_render(self):
        # Get the user instance for the first row
        user = self.table.rows[0].record
        # Use the render_membership method of UserTable
        rendered_column = self.table.columns['membership'].render(user)
        self.assertIn("Beneficiary", str(rendered_column))

    def test_role_column_render(self):
        # Get the user instance for the first row
        user = self.table.rows[0].record
        # Use the render_role method of UserTable
        rendered_column = self.table.columns['role'].render(user)
        self.assertIn("Role 1", str(rendered_column))
