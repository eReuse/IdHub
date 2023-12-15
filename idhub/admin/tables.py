import django_tables2 as tables
from django.utils.html import format_html

from idhub.models import (
        Rol,
        Event,
        Service,
        VerificableCredential,
        DID,
        File_datas,
        Schemas
)
from idhub_auth.models import User


class ButtonColumn(tables.Column):
    attrs = {
        "a": {
            "type": "button",
            "class": "text-primary",
        }
    }
    # it makes no sense to order a column of buttons
    orderable = False
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
            orderable=False
    )

    membership = tables.Column(empty_values=())
    role = tables.Column(empty_values=())

    def render_view_user(self):
        return format_html('<i class="bi bi-eye"></i>')

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
    view_role = ButtonColumn(
            linkify={
                "viewname": "idhub:admin_rol_edit",
                "args": [tables.A("pk")]
            },
            orderable=False
    )

    delete_role = ButtonColumn(
            linkify={
                "viewname": "idhub:admin_rol_del",
                "args": [tables.A("pk")]
            },
            orderable=False
    )

    def render_view_role(self):
        return format_html('<i class="bi bi-pencil-square"></i>')

    def render_delete_role(self):
        return format_html('<i class="bi bi-trash">')

    class Meta:
        model = Rol
        template_name = "idhub/custom_table.html"
        fields = ("name", "description")


class ServicesTable(tables.Table):
    domain = tables.Column(verbose_name="Service")
    role = tables.Column(empty_values=())
    edit_service = ButtonColumn(
            linkify={
                "viewname": "idhub:admin_service_edit",
                "args": [tables.A("pk")]
                },
            orderable=False
            )

    delete_service = ButtonColumn(
            linkify={
                "viewname": "idhub:admin_service_del",
                "args": [tables.A("pk")]
                },
            orderable=False
            )

    def render_role(self, record):
        return record.get_roles()

    def render_edit_service(self):
        return format_html('<i class="bi bi-pencil-square"></i>')

    def render_delete_service(self):
        return format_html('<i class="bi bi-trash">')

    def order_role(self, queryset, is_descending):
        queryset = queryset.order_by(
            ("-" if is_descending else "") + "rol"
        )

        return (queryset, True)

    class Meta:
        model = Service
        template_name = "idhub/custom_table.html"
        fields = ("domain", "description", "role",
                  "edit_service", "delete_service")


class DashboardTable(tables.Table):
    class Meta:
        model = Event
        template_name = "idhub/custom_table.html"
        fields = ("type", "message", "created")


class CredentialTable(tables.Table):
    type = tables.Column(empty_values=())
    details = tables.Column(empty_values=())
    issued_on = tables.Column(verbose_name="Issued")
    view_credential = ButtonColumn(
            linkify={
                "viewname": "idhub:admin_credential",
                "args": [tables.A("pk")]
                },
            orderable=False
            )

    def render_type(self, record):
        return record.type()

    def render_details(self, record):
        return record.description()

    def render_view_credential(self):
        return format_html('<i class="bi bi-eye"></i>')

    class Meta:
        model = VerificableCredential
        template_name = "idhub/custom_table.html"
        fields = ("type", "details", "issued_on", "status", "user")


class DIDTable(tables.Table):
    created_at = tables.Column(verbose_name="Date")
    did = tables.Column(verbose_name="ID")
    edit_did = ButtonColumn(
            linkify={
                "viewname": "idhub:admin_dids_edit",
                "args": [tables.A("pk")]
                },
            orderable=False,
            verbose_name="Edit DID"
            )
    delete_template_code = """<a class="text-danger"
                            href="javascript:void()"
                            data-bs-toggle="modal"
                            data-bs-target="#confirm-delete-{{ record.id }}"
                            title="Remove"
                            ><i class="bi bi-trash"></i></a>"""
    delete_did = tables.TemplateColumn(template_code=delete_template_code,
                                       orderable=False,
                                       verbose_name="Delete DID")

    def render_edit_did(self):
        return format_html('<i class="bi bi-pencil-square"></i>')

    class Meta:
        model = DID
        template_name = "idhub/custom_table.html"
        fields = ("created_at", "label", "did", "edit_did", "delete_did")


class DataTable(tables.Table):
    created_at = tables.Column(verbose_name="Date")
    file_name = tables.Column(verbose_name="File")

    class Meta:
        model = File_datas
        template_name = "idhub/custom_table.html"
        fields = ("created_at", "file_name", "success")


class TemplateTable(tables.Table):
    view_schema = ButtonColumn(
            linkify={
                "viewname": "idhub:admin_schemas_download",
                "args": [tables.A("pk")]
            },
            orderable=False
    )
    delete_template_code = """<a class="text-danger"
                            href="javascript:void()"
                            data-bs-toggle="modal"
                            data-bs-target="#confirm-delete-{{ record.id }}"
                            title="Remove"
                            ><i class="bi bi-trash"></i></a>"""
    delete_schema = tables.TemplateColumn(template_code=delete_template_code,
                                          orderable=False,
                                          verbose_name="Delete schema")

    class Meta:
        model = Schemas
        template_name = "idhub/custom_table.html"
        fields = ("created_at", "file_schema", "name", "description",
                  "view_schema", "delete_schema")
