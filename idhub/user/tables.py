from django.utils.html import format_html
import django_tables2 as tables
from idhub.models import Event, Membership, UserRol, DID, VerificableCredential


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


class DashboardTable(tables.Table):
    type = tables.Column(verbose_name="Event")
    message = tables.Column(verbose_name="Description")
    created = tables.Column(verbose_name="Date")

    class Meta:
        model = Event
        template_name = "idhub/custom_table.html"
        fields = ("type", "message", "created")


class PersonalInfoTable(tables.Table):
    type = tables.Column(verbose_name="Membership")
    credential = ButtonColumn(
            # TODO: See where this should actually link
            linkify="idhub:user_credentials",
            orderable=False
            )

    def render_credential(self):
        return format_html('<i class="bi bi-eye"></i>')

    class Meta:
        model = Membership
        template_name = "idhub/custom_table.html"
        fields = ("type", "start_date", "end_date", "credential")


class RolesTable(tables.Table):
    name = tables.Column(verbose_name="Role", empty_values=())
    description = tables.Column(empty_values=())
    service = tables.Column()

    def render_name(self, record):
        return record.service.get_roles()

    def render_description(self, record):
        return record.service.description

    def render_service(self, record):
        return record.service.domain

    def order_name(self, queryset, is_descending):
        queryset = queryset.order_by(
                ("-" if is_descending else "") + "service__rol__name"
                )

        return (queryset, True)

    def order_description(self, queryset, is_descending):
        queryset = queryset.order_by(
                ("-" if is_descending else "") + "service__rol__description"
                )

        return (queryset, True)

    class Meta:
        model = UserRol
        template_name = "idhub/custom_table.html"
        fields = ("name", "description", "service")


class DIDTable(tables.Table):
    created_at = tables.Column(verbose_name="Date")
    did = tables.Column(verbose_name="ID")
    edit = ButtonColumn(
            linkify={
                "viewname": "idhub:user_dids_edit",
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
    delete = tables.TemplateColumn(template_code=delete_template_code,
                                   orderable=False)

    def render_edit(self):
        return format_html('<i class="bi bi-pencil-square"></i>')

    class Meta:
        model = DID
        template_name = "idhub/custom_table.html"
        fields = ("created_at", "label", "did", "edit", "delete")


class CredentialsTable(tables.Table):
    description = tables.Column(verbose_name="Details", empty_values=())

    def render_description(self, record):
        return record.get_description

    def render_status(self, record):
        return record.get_status()

    class Meta:
        model = VerificableCredential
        template_name = "idhub/custom_table.html"
        fields = ("type", "description", "issued_on", "status")
