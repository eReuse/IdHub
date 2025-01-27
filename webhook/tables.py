import django_tables2 as tables
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from webhook.models import Token

        
class ButtonRemoveColumn(tables.Column):
    attrs = {
        "a": {
            "type": "button",
            "class": "text-danger",
            "title": "Remove",
        }
    }
    # it makes no sense to order a column of buttons
    orderable = False
    # django_tables will only call the render function if it doesn't find
    # any empty values in the data, so we stop it from matching the data
    # to any value considered empty
    empty_values = ()

    def render(self):
        return format_html('<i class="bi bi-trash"></i>')


class TokensTable(tables.Table):
    delete = ButtonRemoveColumn(
            verbose_name=_("Delete"),
            linkify={
                "viewname": "webhook:delete_token",
                "args": [tables.A("pk")]
            },
            orderable=False
    )
    # active = tables.Column(linkify=lambda record: reverse("webhook:status_token", kwargs={"pk": record.pk}))
    active = tables.Column(
            linkify={
                "viewname": "webhook:status_token",
                "args": [tables.A("pk")]
            }
    )

    token = tables.Column(verbose_name=_("Token"), empty_values=())
    label = tables.Column(verbose_name=_("Label"), empty_values=())

    # def render_view_user(self):
    #     return format_html('<i class="bi bi-eye"></i>')

    # def render_token(self, record):
    #     return record.get_memberships()

    # def order_membership(self, queryset, is_descending):
    #     # TODO: Test that this doesn't return more rows than it should
    #     queryset = queryset.order_by(
    #         ("-" if is_descending else "") + "memberships__type"
    #     )

    #     return (queryset, True)

    # def render_role(self, record):
    #     return record.get_roles()

    # def order_role(self, queryset, is_descending):
    #     queryset = queryset.order_by(
    #         ("-" if is_descending else "") + "roles"
    #     )

    #     return (queryset, True)

    class Meta:
        model = Token
        template_name = "idhub/custom_table.html"
        fields = ("token", "label", "active")

    def render_active(self, value):
        """
        Render icons custom based on active value
        """
        if value:  # if `active` is True
            return format_html('<i class="bi bi-toggle-on text-primary"></i>')
        else:  # if `active` is False
            return format_html('<i class="bi bi-toggle-off text-danger"></i>')
