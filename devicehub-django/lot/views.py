from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import (
    CreateView,
    DeleteView,
    UpdateView,
    FormView,
)
from dashboard.mixins import DashboardView
from lot.models import Lot, LotTag, LotAnnotation
from lot.forms import LotsForm


class NewLotView(DashboardView, CreateView):
    template_name = "new_lot.html"
    title = _("New lot")
    breadcrumb = "lot / New lot"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    model = Lot
    fields = (
        "type",
        "name",
        "code",
        "description",
        "closed",
    )

    def form_valid(self, form):
        form.instance.owner = self.request.user.institution
        form.instance.user = self.request.user
        response = super().form_valid(form)
        return response


class DeleteLotView(DashboardView, DeleteView):
    template_name = "delete_lot.html"
    title = _("Delete lot")
    breadcrumb = "lot / Delete lot"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    model = Lot
    fields = (
        "type",
        "name",
        "code",
        "description",
        "closed",
    )

    def form_valid(self, form):
        response = super().form_valid(form)
        return response


class EditLotView(DashboardView, UpdateView):
    template_name = "new_lot.html"
    title = _("Edit lot")
    breadcrumb = "Lot / Edit lot"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    model = Lot
    fields = (
        "type",
        "name",
        "code",
        "description",
        "closed",
    )

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        self.object = get_object_or_404(
            self.model,
            owner=self.request.user.institution,
            pk=pk,
        )
        # self.success_url = reverse_lazy('dashbiard:lot', args=[pk])
        kwargs = super().get_form_kwargs()
        return kwargs


class AddToLotView(DashboardView, FormView):
    template_name = "list_lots.html"
    title = _("Add to lots")
    breadcrumb = "lot / add to lots"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    form_class = LotsForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lots = Lot.objects.filter(owner=self.request.user.institution)
        lot_tags = LotTag.objects.filter(owner=self.request.user.institution)
        context.update({
            'lots': lots,
            'lot_tags':lot_tags,
        })
        return context

    def get_form(self):
        form = super().get_form()
        form.fields["lots"].queryset = Lot.objects.filter(owner=self.request.user.institution)
        return form

    def form_valid(self, form):
        form.devices = self.get_session_devices()
        form.save()
        response = super().form_valid(form)
        return response


class DelToLotView(AddToLotView):
    title = _("Remove from lots")
    breadcrumb = "lot / remove from lots"

    def form_valid(self, form):
        form.devices = self.get_session_devices()
        form.remove()
        response = super().form_valid(form)
        return response


class LotsTagsView(DashboardView, TemplateView):
    template_name = "lots.html"
    title = _("lots")
    breadcrumb = _("lots") + " /"
    success_url = reverse_lazy('dashboard:unassigned_devices')

    def get_context_data(self, **kwargs):
        self.pk = kwargs.get('pk')
        context = super().get_context_data(**kwargs)
        tag = get_object_or_404(LotTag, owner=self.request.user.institution, id=self.pk)
        self.title += " {}".format(tag.name)
        self.breadcrumb += " {}".format(tag.name)
        show_closed = self.request.GET.get('show_closed', 'false') == 'true'
        lots = Lot.objects.filter(owner=self.request.user.institution).filter(type=tag, closed=show_closed)
        context.update({
            'lots': lots,
            'title': self.title,
            'breadcrumb': self.breadcrumb,
            'show_closed': show_closed
        })
        return context


class LotAddDocumentView(DashboardView, CreateView):
    template_name = "new_annotation.html"
    title = _("New Document")
    breadcrumb = "Device / New document"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    model = LotAnnotation
    fields = ("key", "value")

    def form_valid(self, form):
        form.instance.owner = self.request.user.institution
        form.instance.user = self.request.user
        form.instance.lot = self.lot
        form.instance.type = LotAnnotation.Type.DOCUMENT
        response = super().form_valid(form)
        return response

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        self.lot = get_object_or_404(Lot, pk=pk, owner=self.request.user.institution)
        self.success_url = reverse_lazy('lot:documents', args=[pk])
        kwargs = super().get_form_kwargs()
        return kwargs


class LotDocumentsView(DashboardView, TemplateView):
    template_name = "documents.html"
    title = _("New Document")
    breadcrumb = "Device / New document"

    def get_context_data(self, **kwargs):
        self.pk = kwargs.get('pk')
        context = super().get_context_data(**kwargs)
        lot = get_object_or_404(Lot, owner=self.request.user.institution, id=self.pk)
        documents = LotAnnotation.objects.filter(
            lot=lot,
            owner=self.request.user.institution,
            type=LotAnnotation.Type.DOCUMENT,
        )
        context.update({
            'lot': lot,
            'documents': documents,
            'title': self.title,
            'breadcrumb': self.breadcrumb
        })
        return context


class LotAnnotationsView(DashboardView, TemplateView):
    template_name = "annotations.html"
    title = _("New Annotation")
    breadcrumb = "Device / New annotation"

    def get_context_data(self, **kwargs):
        self.pk = kwargs.get('pk')
        context = super().get_context_data(**kwargs)
        lot = get_object_or_404(Lot, owner=self.request.user.institution, id=self.pk)
        annotations = LotAnnotation.objects.filter(
            lot=lot,
            owner=self.request.user.institution,
            type=LotAnnotation.Type.USER,
        )
        context.update({
            'lot': lot,
            'annotations': annotations,
            'title': self.title,
            'breadcrumb': self.breadcrumb
        })
        return context


class LotAddAnnotationView(DashboardView, CreateView):
    template_name = "new_annotation.html"
    title = _("New Annotation")
    breadcrumb = "Device / New annotation"
    success_url = reverse_lazy('dashboard:unassigned_devices')
    model = LotAnnotation
    fields = ("key", "value")

    def form_valid(self, form):
        form.instance.owner = self.request.user.institution
        form.instance.user = self.request.user
        form.instance.lot = self.lot
        form.instance.type = LotAnnotation.Type.USER
        response = super().form_valid(form)
        return response

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        self.lot = get_object_or_404(Lot, pk=pk, owner=self.request.user.institution)
        self.success_url = reverse_lazy('lot:annotations', args=[pk])
        kwargs = super().get_form_kwargs()
        return kwargs
