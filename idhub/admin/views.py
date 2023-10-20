import os
import logging
from pathlib import Path
from smtplib import SMTPException

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from idhub.models import Membership, Rol, Service, UserRol, Schemas
from idhub.mixins import AdminView
from idhub.email.views import NotifyActivateUserByEmail
from idhub.admin.forms import (
    ProfileForm,
    MembershipForm,
    RolForm,
    ServiceForm,
    UserRolForm
)


class AdminDashboardView(AdminView, TemplateView):
    template_name = "idhub/admin/dashboard.html"
    title = _('Dashboard')
    subtitle = _('Success')
    icon = 'bi bi-bell'
    section = "Home"

class People(AdminView):
    title = _("People Management")
    section = "People"


class AccessControl(AdminView, TemplateView):
    title = _("Access Control Management")
    section = "AccessControl"


class Credentials(AdminView, TemplateView):
    title = _("Credentials Management")
    section = "Credentials"


class SchemasMix(AdminView, TemplateView):
    title = _("Templates Management")
    section = "Templates"


class ImportExport(AdminView, TemplateView):
    title = _("Massive Data Management")
    section = "ImportExport"


class AdminPeopleListView(People, TemplateView):
    template_name = "idhub/admin/people.html"
    subtitle = _('People list')
    icon = 'bi bi-person'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'users': User.objects.filter(),
        })
        return context


class AdminPeopleView(People, TemplateView):
    template_name = "idhub/admin/user.html"
    subtitle = _('User Profile')
    icon = 'bi bi-person'
    model = User

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'object': self.object,
        })
        return context


class AdminPeopleActivateView(AdminPeopleView):

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        if self.object == self.request.user:
            messages.error(self.request, _('Is not possible deactivate your account!'))
            return redirect('idhub:admin_people', self.object.id)

        if self.object.is_active:
            self.object.is_active = False
        else:
            self.object.is_active = True
        self.object.save()

        return redirect('idhub:admin_people', self.object.id)
            

class AdminPeopleDeleteView(AdminPeopleView):

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        if self.object != self.request.user:
            self.object.delete()
        else:
            messages.error(self.request, _('Is not possible delete your account!'))

        return redirect('idhub:admin_people_list')
            
class AdminPeopleEditView(AdminPeopleView, UpdateView):
    template_name = "idhub/admin/user_edit.html"
    from_class = ProfileForm
    fields = ('first_name', 'last_name', 'email', 'username')
    success_url = reverse_lazy('idhub:admin_people_list')


class AdminPeopleRegisterView(NotifyActivateUserByEmail, People, CreateView):
    template_name = "idhub/admin/people_register.html"
    subtitle = _('People Register')
    icon = 'bi bi-person'
    model = User
    from_class = ProfileForm
    fields = ('first_name', 'last_name', 'email', 'username')
    success_url = reverse_lazy('idhub:admin_people_list')

    def get_success_url(self):
        self.success_url = reverse_lazy(
            'idhub:admin_people_membership_new',
            kwargs={"pk": self.object.id}
        )
        return self.success_url

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, _('The account is created successfully'))
        if user.is_active:
            try:
                self.send_email(user)
            except SMTPException as e:
                messages.error(self.request, e)
        return super().form_valid(form)


class AdminPeopleMembershipRegisterView(People, CreateView):
    template_name = "idhub/admin/people_membership_register.html"
    subtitle = _('People add membership')
    icon = 'bi bi-person'
    model = Membership
    from_class = MembershipForm
    fields = ('type', 'start_date', 'end_date')
    success_url = reverse_lazy('idhub:admin_people_list')

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.user = get_object_or_404(User, pk=self.pk)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.user = get_object_or_404(User, pk=self.pk)
        return super().post(request, *args, **kwargs)

    def get_form(self):
        form = super().get_form()
        form.fields['start_date'].widget.input_type = 'date'
        form.fields['end_date'].widget.input_type = 'date'
        return form

    def get_form_kwargs(self):
        self.object = self.model(user=self.user)
        kwargs = super().get_form_kwargs()
        return kwargs

    def get_success_url(self):
        self.success_url = reverse_lazy(
            'idhub:admin_people_rol_new',
            kwargs={"pk": self.user.id}
        )
        return self.success_url


class AdminPeopleMembershipEditView(People, CreateView):
    template_name = "idhub/admin/people_membership_register.html"
    subtitle = _('People add membership')
    icon = 'bi bi-person'
    model = Membership
    from_class = MembershipForm
    fields = ('type', 'start_date', 'end_date')
    success_url = reverse_lazy('idhub:admin_people_list')

    def get_form(self):
        form = super().get_form()
        form.fields['start_date'].widget.input_type = 'date'
        form.fields['end_date'].widget.input_type = 'date'
        return form

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        if pk:
            self.object = get_object_or_404(self.model, pk=pk)
        kwargs = super().get_form_kwargs()
        return kwargs


class AdminPeopleMembershipDeleteView(AdminPeopleView):
    model = Membership

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        if self.object != self.request.user:
            user = self.object.user
            self.object.delete()
        else:
            messages.error(self.request, _('Is not possible delete your account!'))

        return redirect('idhub:admin_people_edit', user.id)

        
class AdminPeopleRolRegisterView(People, CreateView):
    template_name = "idhub/admin/people_rol_register.html"
    subtitle = _('Add Rol to User')
    icon = 'bi bi-person'
    model = UserRol
    from_class = UserRolForm
    fields = ('service',)

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.user = get_object_or_404(User, pk=self.pk)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.user = get_object_or_404(User, pk=self.pk)
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        self.object = self.model(user=self.user)
        kwargs = super().get_form_kwargs()
        return kwargs

    def get_success_url(self):
        self.success_url = reverse_lazy(
            'idhub:admin_people_edit',
            kwargs={"pk": self.user.id}
        )
        return self.success_url


class AdminPeopleRolEditView(People, CreateView):
    template_name = "idhub/admin/people_rol_register.html"
    subtitle = _('Edit Rol to User')
    icon = 'bi bi-person'
    model = UserRol
    from_class = UserRolForm
    fields = ('service',)

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        if pk:
            self.object = get_object_or_404(self.model, pk=pk)
        kwargs = super().get_form_kwargs()
        return kwargs

    def get_success_url(self):
        self.success_url = reverse_lazy(
            'idhub:admin_people_edit',
            kwargs={"pk": self.object.user.id}
        )
        return self.success_url


class AdminPeopleRolDeleteView(AdminPeopleView):
    model = UserRol

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        user = self.object.user

        self.object.delete()

        return redirect('idhub:admin_people_edit', user.id)


class AdminRolesView(AccessControl):
    template_name = "idhub/admin/roles.html"
    subtitle = _('Roles Management')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'roles': Rol.objects,
        })
        return context

class AdminRolRegisterView(AccessControl, CreateView):
    template_name = "idhub/admin/rol_register.html"
    subtitle = _('Add Rol')
    icon = ''
    model = Rol
    from_class = RolForm
    fields = ('name',)
    success_url = reverse_lazy('idhub:admin_roles')
    object = None

        
class AdminRolEditView(AccessControl, CreateView):
    template_name = "idhub/admin/rol_register.html"
    subtitle = _('Edit Rol')
    icon = ''
    model = Rol
    from_class = RolForm
    fields = ('name',)
    success_url = reverse_lazy('idhub:admin_roles')

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        if pk:
            self.object = get_object_or_404(self.model, pk=pk)
        kwargs = super().get_form_kwargs()
        return kwargs


class AdminRolDeleteView(AccessControl):
    model = Rol

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        self.object.delete()
        return redirect('idhub:admin_roles')


class AdminServicesView(AccessControl):
    template_name = "idhub/admin/services.html"
    subtitle = _('Service Management')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'services': Service.objects,
        })
        return context

class AdminServiceRegisterView(AccessControl, CreateView):
    template_name = "idhub/admin/service_register.html"
    subtitle = _('Add Service')
    icon = ''
    model = Service
    from_class = ServiceForm
    fields = ('domain', 'description', 'rol')
    success_url = reverse_lazy('idhub:admin_services')
    object = None

        
class AdminServiceEditView(AccessControl, CreateView):
    template_name = "idhub/admin/service_register.html"
    subtitle = _('Edit Service')
    icon = ''
    model = Service
    from_class = ServiceForm
    fields = ('domain', 'description', 'rol')
    success_url = reverse_lazy('idhub:admin_services')

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        if pk:
            self.object = get_object_or_404(self.model, pk=pk)
        kwargs = super().get_form_kwargs()
        return kwargs


class AdminServiceDeleteView(AccessControl):
    model = Service

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        self.object.delete()
        return redirect('idhub:admin_services')


class AdminCredentialsView(Credentials):
    template_name = "idhub/admin/credentials.html"
    subtitle = _('Credentials list')
    icon = ''


class AdminIssueCredentialsView(Credentials):
    template_name = "idhub/admin/issue_credentials.html"
    subtitle = _('Issuance of Credentials')
    icon = ''


class AdminRevokeCredentialsView(Credentials):
    template_name = "idhub/admin/revoke_credentials.html"
    subtitle = _('Revoke Credentials')
    icon = ''


class AdminWalletIdentitiesView(Credentials):
    template_name = "idhub/admin/wallet_identities.html"
    subtitle = _('Organization Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True


class AdminWalletCredentialsView(Credentials):
    template_name = "idhub/admin/wallet_credentials.html"
    subtitle = _('Credentials')
    icon = 'bi bi-patch-check-fill'
    wallet = True


class AdminWalletConfigIssuesView(Credentials):
    template_name = "idhub/admin/wallet_issues.html"
    subtitle = _('Configure Issues')
    icon = 'bi bi-patch-check-fill'
    wallet = True


class AdminSchemasView(SchemasMix):
    template_name = "idhub/admin/schemas.html"
    subtitle = _('Template List')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'schemas': Schemas.objects,
        })
        return context


class AdminSchemasImportView(SchemasMix):
    template_name = "idhub/admin/schemas_import.html"
    subtitle = _('Import Template')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'schemas': self.get_schemas(),
        })
        return context

    def get_schemas(self):
        schemas_files = os.listdir(settings.SCHEMAS_DIR)
        schemas = [x for x  in schemas_files 
            if not Schemas.objects.filter(file_schema=x).exists()]
        return schemas

        
class AdminSchemasImportAddView(SchemasMix):

    def get(self, request, *args, **kwargs):
        file_name = kwargs['file_schema']
        schemas_files = os.listdir(settings.SCHEMAS_DIR)
        if not file_name in schemas_files:
            messages.error(self.request, f"The schema {file_name} not exist!")
            return redirect('idhub:admin_schemas_import')

        self.create_schema(file_name)
        messages.success(self.request, _("The schema add successfully!"))
        return redirect('idhub:admin_schemas_import')

    def create_schema(self, file_name):
        data = self.open_file(file_name)
        schema = Schemas.objects.create(file_schema=file_name, data=data)
        schema.save()
        return schema

    def open_file(self, file_name):
        data = ''
        filename = Path(settings.SCHEMAS_DIR).joinpath(file_name)
        with filename.open() as schema_file:
            data = schema_file.read()

        return data


class AdminSchemasExportView(SchemasMix):
    template_name = "idhub/admin/schemas_export.html"
    subtitle = _('Export Template')
    icon = ''


class AdminImportView(ImportExport):
    template_name = "idhub/admin/import.html"
    subtitle = _('Import')
    icon = ''


class AdminExportView(ImportExport):
    template_name = "idhub/admin/export.html"
    subtitle = _('Export')
    icon = ''
