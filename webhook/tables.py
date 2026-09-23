from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
import django_tables2 as tables

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
    token = tables.Column(verbose_name=_("Token UUID"), orderable=False)
    allowed_dids = tables.Column(verbose_name=_("Allowed DIDs"), empty_values=(), orderable=False)
    active = tables.Column(verbose_name=_("Status"))
    actions = tables.Column(verbose_name=_("Actions"), empty_values=(), orderable=False)

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
    #
    def render_token(self, value):
        token_str = str(value)
        short_token = f"{token_str[:8]}...{token_str[-4:]}"
        return format_html(
            '''
            <div class="d-inline-flex align-items-center gap-2">
                <code class="text-dark bg-light px-2 py-1 rounded border" title="{0}">{1}</code>
                <button type="button"
                        class="btn btn-sm btn-outline-secondary copy-token-btn"
                        data-token="{0}"
                        title="{2}">
                    <i class="bi bi-clipboard"></i>
                </button>
            </div>
            ''',
            token_str,
            short_token,
            _("Copy to clipboard")
        )

    def render_actions(self, record):
        edit_url = reverse("webhook:token_edit", args=[record.pk])
        return format_html(
            '''
            <a href="{}" class="btn btn-sm btn-outline-primary d-inline-flex align-items-center gap-1">
                {}
            </a>
            ''',
            edit_url,
            _("Edit")
        )

    def render_active(self, value):
        if value:
            return format_html('<span class="badge bg-success">{}</span>', _("Active"))
        return format_html('<span class="badge bg-danger">{}</span>', _("Disabled"))

    def render_allowed_dids(self, record):
        dids = list(record.allowed_dids.all())

        if not dids:
            return format_html(
                '<span class="badge bg-secondary text-light" title="{}">{}</span>',
                _("This token has no access to any DIDs"),
                _("None (No Access)")
            )

        max_visible = 2
        visible_dids = dids[:max_visible]
        extra_count = len(dids) - max_visible

        badges = []
        for d in visible_dids:
            display_text = d.label if hasattr(d, 'label') and d.label else d.did.split(':')[-1]
            badges.append(
                f'<span class="badge bg-light text-dark border me-1" title="{d.did}">{display_text}</span>'
            )

        html_output = "".join(badges)

        if extra_count > 0:
            all_dids_str = ", ".join([d.did for d in dids])
            html_output += f'<span class="badge bg-info text-dark" title="{all_dids_str}">+{extra_count} more</span>'

        return mark_safe(f'<div class="d-flex flex-wrap gap-1">{html_output}</div>')

    class Meta:
        model = Token
        fields = ("label", "token", "allowed_dids", "active", "actions")
        template_name = "idhub/custom_table.html"
