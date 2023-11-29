import django_tables2 as tables
from django.utils.html import format_html

from idhub.models import Rol, Event
from idhub_auth.models import User


class ButtonColumn(tables.Column):
    attrs = {
        "a": {
            "type": "button",
            "class": "text-primary",
            "title": "'View'",
        }
    }
    # django_tables will only call the render function if it doesn't find
    # any empty values in the data, so we stop it from matching the data
    # to any value considered empty
    empty_values = ()

    def render(self):
        return format_html('<i class="bi bi-eye"></i>')


class UserTable(tables.Table):
    view_user = ButtonColumn(
            linkify={
                "viewname": "idhub:admin_people",
                "args": [tables.A("pk")]
            },
            orderable=False,
            )
    membership = tables.Column(empty_values=())
    role = tables.Column(empty_values=())

    def render_membership(self, record):
        return record.get_memberships()

    def order_membership(self, queryset, is_descending):
        # TODO: Test that this doesn't return more rows than it should
        queryset = queryset.order_by(
            ("-" if is_descending else "") + "memberships__type"
        )

        return (queryset, True)

    def render_role(self, record):
        return record.get_roles()

    def order_role(self, queryset, is_descending):
        queryset = queryset.order_by(
            ("-" if is_descending else "") + "roles"
        )

        return (queryset, True)

    class Meta:
        model = User
        template_name = "idhub/custom_table.html"
        fields = ("last_name", "first_name", "email", "membership", "role",
                  "view_user")


class RolesTable(tables.Table):
    class Meta:
        model = Rol
        template_name = "idhub/custom_table.html"
        fields = ("name", "description")


class DashboardTable(tables.Table):
    class Meta:
        model = Event
        template_name = "idhub/custom_table.html"
        fields = ("type", "message", "created")
