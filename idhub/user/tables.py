import django_tables2 as tables
from idhub.models import Event


class DashboardTable(tables.Table):
    type = tables.Column(verbose_name="Event")
    message = tables.Column(verbose_name="Description")
    created = tables.Column(verbose_name="Date")

    class Meta:
        model = Event
        template_name = "idhub/custom_table.html"
        fields = ("type", "message", "created")
