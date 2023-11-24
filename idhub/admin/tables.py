import django_tables2 as tables
from idhub.models import Rol, Event
from idhub_auth.models import User


class UserTable(tables.Table):
    class Meta:
        model = User
        template_name = "idhub/custom_table.html"
        fields = ("first_name", "last_name", "email", "is_active", "is_admin")


class RolesTable(tables.Table):
    class Meta:
        model = Rol
        template_name = "idhub/custom_table.html"
        fields = ("name", "description")


class DashboardTable(tables.Table):
    type = tables.Column(verbose_name="Event")
    message = tables.Column(verbose_name="Description")
    created = tables.Column(verbose_name="Date")

    class Meta:
        model = Event
        template_name = "idhub/custom_table.html"
        fields = ("type", "message", "created")
