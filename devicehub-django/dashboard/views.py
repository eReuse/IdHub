import json

from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView
from django.shortcuts import Http404
from django.db.models import Q

from dashboard.mixins import InventaryMixin, DetailsMixin
from evidence.models import Annotation
from evidence.xapian import search
from device.models import Device
from lot.models import Lot


class UnassignedDevicesView(InventaryMixin):
    template_name = "unassigned_devices.html"
    section = "Unassigned"
    title = _("Unassigned Devices")
    breadcrumb = "Devices / Unassigned Devices"

    def get_devices(self, user, offset, limit):
        return Device.get_unassigned(self.request.user.institution, offset, limit)


class LotDashboardView(InventaryMixin, DetailsMixin):
    template_name = "unassigned_devices.html"
    section = "dashboard_lot"
    title = _("Lot Devices")
    breadcrumb = "Lot / Devices"
    model = Lot

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lot = context.get('object')
        context.update({
            'lot': lot,
        })
        return context

    def get_devices(self, user, offset, limit):
        chids = self.object.devicelot_set.all().values_list(
            "device_id", flat=True
        ).distinct()

        chids_page = chids[offset:offset+limit]
        return [Device(id=x) for x in chids_page], chids.count()


class SearchView(InventaryMixin):
    template_name = "unassigned_devices.html"
    section = "Search"
    title = _("Search Devices")
    breadcrumb = "Devices / Search Devices"

    def get_devices(self, user, offset, limit):
        post = dict(self.request.POST)
        query = post.get("search")

        if not query:
            return [], 0

        matches = search(
            self.request.user.institution,
            query[0],
            offset,
            limit
        )

        if not matches or not matches.size():
            return self.search_hids(query, offset, limit)

        devices = []
        dev_id = []

        for x in matches:
            # devices.append(self.get_annotations(x))
            dev = self.get_annotations(x)
            if dev.id not in dev_id:
                devices.append(dev)
                dev_id.append(dev.id)

        count = matches.size()
        # TODO fix of pagination, the count is not correct
        return devices, count

    def get_annotations(self, xp):
        snap = xp.document.get_data()
        uuid = json.loads(snap).get('uuid')
        return Device.get_annotation_from_uuid(uuid, self.request.user.institution)

    def search_hids(self, query, offset, limit):
        qry = Q()

        for i in query[0].split(" "):
            if i:
                qry |= Q(value__startswith=i)

        chids = Annotation.objects.filter(
            type=Annotation.Type.SYSTEM,
            owner=self.request.user.institution
        ).filter(
            qry
        ).values_list("value", flat=True).distinct()
        chids_page = chids[offset:offset+limit]

        return [Device(id=x) for x in chids_page], chids.count()
