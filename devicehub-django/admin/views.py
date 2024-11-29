from smtplib import SMTPException
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import (
    CreateView,
    UpdateView,
    DeleteView,
)
from dashboard.mixins import DashboardView, Http403
from user.models import User, Institution
from admin.email import NotifyActivateUserByEmail


class AdminView(DashboardView):
    def get(self, *args, **kwargs):
        response = super().get(*args, **kwargs)
        if not self.request.user.is_admin:
            raise Http403
        
        return response

class PanelView(AdminView, TemplateView):
    template_name = "admin_panel.html"
    title = _("Admin")
    breadcrumb = _("admin") + " /"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class UsersView(AdminView, TemplateView):
    template_name = "admin_users.html"
    title = _("Users")
    breadcrumb = _("admin / Users") + " /"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "users": User.objects.filter()
        })
        return context


class CreateUserView(AdminView, NotifyActivateUserByEmail, CreateView):
    template_name = "user.html"
    title = _("User")
    breadcrumb = _("admin / User") + " /"
    success_url = reverse_lazy('admin:users')
    model = User
    fields = (
        "email",
        "password",
        "is_admin",
    )

    def form_valid(self, form):
        form.instance.institution = self.request.user.institution
        form.instance.set_password(form.instance.password)
        response = super().form_valid(form)

        try:
            self.send_email(form.instance)
        except SMTPException as e:
            messages.error(self.request, e)

        return response


class DeleteUserView(AdminView, DeleteView):
    template_name = "delete_user.html"
    title = _("Delete user")
    breadcrumb = "admin / Delete user"
    success_url = reverse_lazy('admin:users')
    model = User
    fields = (
        "email",
        "password",
        "is_admin",
    )

    def form_valid(self, form):
        response = super().form_valid(form)
        return response


class EditUserView(AdminView, UpdateView):
    template_name = "user.html"
    title = _("Edit user")
    breadcrumb = "admin / Edit user"
    success_url = reverse_lazy('admin:users')
    model = User
    fields = (
        "email",
        "is_admin",
    )

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        self.object = get_object_or_404(self.model, pk=pk)
        #self.object.set_password(self.object.password)
        kwargs = super().get_form_kwargs()
        return kwargs

    
class InstitutionView(AdminView, UpdateView):
    template_name = "institution.html"
    title = _("Edit institution")
    section = "admin"
    subtitle = _('Edit institution')
    model = Institution
    success_url = reverse_lazy('admin:panel')
    fields = (
        "name",
        "logo",
        "location",
        "responsable_person",
        "supervisor_person"
    )

    def get_form_kwargs(self):
        self.object = self.request.user.institution
        kwargs = super().get_form_kwargs()
        return kwargs
