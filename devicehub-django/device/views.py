import json
from django.http import JsonResponse

from django.http import Http404
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import (
    CreateView,
    UpdateView,
    FormView,
)
from django.views.generic.base import TemplateView
from dashboard.mixins import DashboardView, Http403
from evidence.models import Annotation
from lot.models import LotTag
from dpp.models import Proof
from device.models import Device
from device.forms import DeviceFormSet


class NewDeviceView(DashboardView, FormView):
    template_name = "new_device.html"
    title = _("New Device")
    breadcrumb = "Device / New Device"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    form_class = DeviceFormSet

    def form_valid(self, form):
        form.save(self.request.user)
        response = super().form_valid(form)
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        return response


# class AddToLotView(DashboardView, FormView):
#     template_name = "list_lots.html"
#     title = _("Add to lots")
#     breadcrumb = "lot / add to lots"
#     success_url = reverse_lazy('dashboard:unassigned_devices')
#     form_class = LotsForm

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         lots = Lot.objects.filter(owner=self.request.user)
#         lot_tags = LotTag.objects.filter(owner=self.request.user)
#         context.update({
#             'lots': lots,
#             'lot_tags':lot_tags,
#         })
#         return context

#     def get_form(self):
#         form = super().get_form()
#         form.fields["lots"].queryset = Lot.objects.filter(owner=self.request.user)
#         return form

#     def form_valid(self, form):
#         form.devices = self.get_session_devices()
#         form.save()
#         response = super().form_valid(form)
#         return response


class EditDeviceView(DashboardView, UpdateView):
    template_name = "new_device.html"
    title = _("Update Device")
    breadcrumb = "Device / Update Device"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    model = Annotation

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        self.object = get_object_or_404(
            self.model,
            pk=pk,
            owner=self.request.user.institution
        )
        self.success_url = reverse_lazy('device:details', args=[pk])
        kwargs = super().get_form_kwargs()
        return kwargs


class DetailsView(DashboardView, TemplateView):
    template_name = "details.html"
    title = _("Device")
    breadcrumb = "Device / Details"
    model = Annotation

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = Device(id=self.pk)
        if not self.object.last_evidence:
            raise Http404
        if self.object.owner != self.request.user.institution:
            raise Http403

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object.initial()
        lot_tags = LotTag.objects.filter(owner=self.request.user.institution)
        dpps = Proof.objects.filter(uuid__in=self.object.uuids)
        context.update({
            'object': self.object,
            'snapshot': self.object.get_last_evidence(),
            'lot_tags': lot_tags,
            'dpps': dpps,
        })
        return context


class PublicDeviceWebView(TemplateView):
    template_name = "device_web.html"

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = Device(id=self.pk)

        if not self.object.last_evidence:
            raise Http404

        if self.request.headers.get('Accept') == 'application/json':
            return self.get_json_response()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object.initial()
        context.update({
            'object': self.object
        })
        return context

    @property
    def public_fields(self):
        return {
            'id': self.object.id,
            'shortid': self.object.shortid,
            'uuids': self.object.uuids,
            'hids': self.object.hids,
            'components': self.remove_serial_number_from(self.object.components),
        }

    @property
    def authenticated_fields(self):
        return {
            'serial_number': self.object.serial_number,
            'components': self.object.components,
        }

    def remove_serial_number_from(self, components):
        for component in components:
            if 'serial_number' in component:
                del component['SerialNumber']
        return components

    def get_device_data(self):
        data = self.public_fields
        if self.request.user.is_authenticated:
            data.update(self.authenticated_fields)
        return data

    def get_json_response(self):
        device_data = self.get_device_data()
        return JsonResponse(device_data)


class AddAnnotationView(DashboardView, CreateView):
    template_name = "new_annotation.html"
    title = _("New annotation")
    breadcrumb = "Device / New annotation"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    model = Annotation
    fields = ("key", "value")

    def form_valid(self, form):
        form.instance.owner = self.request.user.institution
        form.instance.user = self.request.user
        form.instance.uuid = self.annotation.uuid
        form.instance.type = Annotation.Type.USER
        response = super().form_valid(form)
        return response

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        institution = self.request.user.institution
        self.annotation = Annotation.objects.filter(
            owner=institution,
            value=pk,
            type=Annotation.Type.SYSTEM
        ).first()

        if not self.annotation:
            raise Http404

        self.success_url = reverse_lazy('device:details', args=[pk])
        kwargs = super().get_form_kwargs()
        return kwargs


class AddDocumentView(DashboardView, CreateView):
    template_name = "new_annotation.html"
    title = _("New Document")
    breadcrumb = "Device / New document"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    model = Annotation
    fields = ("key", "value")

    def form_valid(self, form):
        form.instance.owner = self.request.user.institution
        form.instance.user = self.request.user
        form.instance.uuid = self.annotation.uuid
        form.instance.type = Annotation.Type.DOCUMENT
        response = super().form_valid(form)
        return response

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        institution = self.request.user.institution
        self.annotation = Annotation.objects.filter(
            owner=institution,
            value=pk,
            type=Annotation.Type.SYSTEM
        ).first()

        if not self.annotation:
            raise Http404

        self.success_url = reverse_lazy('device:details', args=[pk])
        kwargs = super().get_form_kwargs()
        return kwargs
