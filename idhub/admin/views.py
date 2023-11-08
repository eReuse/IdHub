import os
import json
import copy
import logging
import pandas as pd
from pathlib import Path
from jsonschema import validate
from smtplib import SMTPException

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import (
    CreateView,
    DeleteView,
    FormView,
    UpdateView,
)
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib import messages
from utils.apiregiter import iota
from utils import credtools
from idhub_auth.models import User
from idhub.mixins import AdminView
from idhub.email.views import NotifyActivateUserByEmail
from idhub.admin.forms import ImportForm, SchemaForm
from idhub.models import (
    DID,
    File_datas,
    Membership,
    Rol,
    Service,
    Schemas,
    UserRol,
    VerificableCredential,
)


class DashboardView(AdminView, TemplateView):
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


class ImportExport(AdminView):
    title = _("Massive Data Management")
    section = "ImportExport"


class PeopleListView(People, TemplateView):
    template_name = "idhub/admin/people.html"
    subtitle = _('People list')
    icon = 'bi bi-person'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'users': User.objects.filter(),
        })
        return context


class PeopleView(People, TemplateView):
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


class PeopleActivateView(PeopleView):

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
            

class PeopleDeleteView(PeopleView):

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        if self.object != self.request.user:
            self.object.delete()
        else:
            messages.error(self.request, _('Is not possible delete your account!'))

        return redirect('idhub:admin_people_list')
            
class PeopleEditView(PeopleView, UpdateView):
    template_name = "idhub/admin/user_edit.html"
    fields = ('first_name', 'last_name', 'email')
    success_url = reverse_lazy('idhub:admin_people_list')


class PeopleRegisterView(NotifyActivateUserByEmail, People, CreateView):
    template_name = "idhub/admin/people_register.html"
    subtitle = _('People Register')
    icon = 'bi bi-person'
    model = User
    fields = ('first_name', 'last_name', 'email')
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


class PeopleMembershipRegisterView(People, CreateView):
    template_name = "idhub/admin/people_membership_register.html"
    subtitle = _('People add membership')
    icon = 'bi bi-person'
    model = Membership
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


class PeopleMembershipEditView(People, CreateView):
    template_name = "idhub/admin/people_membership_register.html"
    subtitle = _('People add membership')
    icon = 'bi bi-person'
    model = Membership
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


class PeopleMembershipDeleteView(PeopleView):
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

        
class PeopleRolRegisterView(People, CreateView):
    template_name = "idhub/admin/people_rol_register.html"
    subtitle = _('Add Rol to User')
    icon = 'bi bi-person'
    model = UserRol
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


class PeopleRolEditView(People, CreateView):
    template_name = "idhub/admin/people_rol_register.html"
    subtitle = _('Edit Rol to User')
    icon = 'bi bi-person'
    model = UserRol
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


class PeopleRolDeleteView(PeopleView):
    model = UserRol

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        user = self.object.user

        self.object.delete()

        return redirect('idhub:admin_people_edit', user.id)


class RolesView(AccessControl):
    template_name = "idhub/admin/roles.html"
    subtitle = _('Roles Management')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'roles': Rol.objects,
        })
        return context

class RolRegisterView(AccessControl, CreateView):
    template_name = "idhub/admin/rol_register.html"
    subtitle = _('Add Rol')
    icon = ''
    model = Rol
    fields = ('name',)
    success_url = reverse_lazy('idhub:admin_roles')
    object = None

        
class RolEditView(AccessControl, CreateView):
    template_name = "idhub/admin/rol_register.html"
    subtitle = _('Edit Rol')
    icon = ''
    model = Rol
    fields = ('name',)
    success_url = reverse_lazy('idhub:admin_roles')

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        if pk:
            self.object = get_object_or_404(self.model, pk=pk)
        kwargs = super().get_form_kwargs()
        return kwargs


class RolDeleteView(AccessControl):
    model = Rol

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        self.object.delete()
        return redirect('idhub:admin_roles')


class ServicesView(AccessControl):
    template_name = "idhub/admin/services.html"
    subtitle = _('Service Management')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'services': Service.objects,
        })
        return context

class ServiceRegisterView(AccessControl, CreateView):
    template_name = "idhub/admin/service_register.html"
    subtitle = _('Add Service')
    icon = ''
    model = Service
    fields = ('domain', 'description', 'rol')
    success_url = reverse_lazy('idhub:admin_services')
    object = None

        
class ServiceEditView(AccessControl, CreateView):
    template_name = "idhub/admin/service_register.html"
    subtitle = _('Edit Service')
    icon = ''
    model = Service
    fields = ('domain', 'description', 'rol')
    success_url = reverse_lazy('idhub:admin_services')

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        if pk:
            self.object = get_object_or_404(self.model, pk=pk)
        kwargs = super().get_form_kwargs()
        return kwargs


class ServiceDeleteView(AccessControl):
    model = Service

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        self.object.delete()
        return redirect('idhub:admin_services')


class CredentialsView(Credentials):
    template_name = "idhub/admin/credentials.html"
    subtitle = _('Credentials list')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'credentials': VerificableCredential.objects,
        })
        return context


class CredentialView(Credentials):
    template_name = "idhub/admin/issue_credentials.html"
    subtitle = _('Change status of Credential')
    icon = ''
    model = VerificableCredential

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


class CredentialJsonView(Credentials):

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
        )
        response = HttpResponse(self.object.data, content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename={}'.format("credential.json")
        return response


class RevokeCredentialsView(Credentials):
    success_url = reverse_lazy('idhub:admin_credentials')

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
        )
        if self.object.status == VerificableCredential.Status.ISSUED:
            self.object.status = VerificableCredential.Status.REVOKED
            self.object.save()
            messages.success(self.request, _('Credential revoked successfully'))

        return redirect(self.success_url)


class DeleteCredentialsView(Credentials):
    success_url = reverse_lazy('idhub:admin_credentials')

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
        )
        status = [
            VerificableCredential.Status.REVOKED,
            VerificableCredential.Status.ISSUED
        ]
        if self.object.status in status:
            self.object.delete()
            messages.success(self.request, _('Credential deleted successfully'))

        return redirect(self.success_url)


class DidsView(Credentials):
    template_name = "idhub/admin/dids.html"
    subtitle = _('Organization Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'dids': DID.objects,
        })
        return context

class DidRegisterView(Credentials, CreateView):
    template_name = "idhub/admin/did_register.html"
    subtitle = _('Add a new Organization Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('label',)
    success_url = reverse_lazy('idhub:admin_dids')
    object = None

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.did = iota.issue_did()
        form.save()
        messages.success(self.request, _('DID created successfully'))
        return super().form_valid(form)


class DidEditView(Credentials, UpdateView):
    template_name = "idhub/admin/did_register.html"
    subtitle = _('Organization Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('label',)
    success_url = reverse_lazy('idhub:admin_dids')

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, _('DID updated successfully'))
        return super().form_valid(form)


class DidDeleteView(Credentials, DeleteView):
    subtitle = _('Organization Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    success_url = reverse_lazy('idhub:admin_dids')

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        self.object.delete()
        messages.success(self.request, _('DID delete successfully'))

        return redirect(self.success_url)


class WalletCredentialsView(Credentials):
    template_name = "idhub/admin/wallet_credentials.html"
    subtitle = _('Credentials')
    icon = 'bi bi-patch-check-fill'
    wallet = True


class WalletConfigIssuesView(Credentials):
    template_name = "idhub/admin/wallet_issues.html"
    subtitle = _('Configure Issues')
    icon = 'bi bi-patch-check-fill'
    wallet = True


class SchemasView(SchemasMix):
    template_name = "idhub/admin/schemas.html"
    subtitle = _('Template List')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'schemas': Schemas.objects,
        })
        return context

        
class SchemasDeleteView(SchemasMix):

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(Schemas, pk=self.pk)
        self.object.delete()

        return redirect('idhub:admin_schemas')


class SchemasDownloadView(SchemasMix):

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(Schemas, pk=self.pk)

        response = HttpResponse(self.object.data, content_type="application/json")
        response['Content-Disposition'] = 'inline; filename={}'.format(self.object.file_schema)
        return response


class SchemasNewView(SchemasMix):
    template_name = "idhub/admin/schemas_new.html"
    subtitle = _('Upload Template')
    icon = ''
    success_url = reverse_lazy('idhub:admin_schemas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form': SchemaForm(),
        })
        return context

    def post(self, request, *args, **kwargs):
        form = SchemaForm(request.POST, request.FILES)
        if form.is_valid():
            schema = self.handle_uploaded_file()
            if not schema:
                messages.error(request, _("There are some errors in the file"))
                return super().get(request, *args, **kwargs)
            return redirect(self.success_url)
        else:
            return super().get(request, *args, **kwargs)

        return super().post(request, *args, **kwargs)

    def handle_uploaded_file(self):
        f = self.request.FILES.get('file_template')
        if not f:
            return
        file_name = f.name
        if Schemas.objects.filter(file_schema=file_name).exists():
            messages.error(self.request, _("This template already exists!"))
            return
        try:
            data = f.read().decode('utf-8')
            json.loads(data)
        except Exception:
            messages.error(self.request, _('This is not a schema valid!'))
            return
        schema = Schemas.objects.create(file_schema=file_name, data=data)
        schema.save()
        return schema


class SchemasImportView(SchemasMix):
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

        
class SchemasImportAddView(SchemasMix):

    def get(self, request, *args, **kwargs):
        file_name = kwargs['file_schema']
        schemas_files = os.listdir(settings.SCHEMAS_DIR)
        if not file_name in schemas_files:
            messages.error(self.request, f"The schema {file_name} not exist!")
            return redirect('idhub:admin_schemas_import')

        schema = self.create_schema(file_name)
        if schema:
            messages.success(self.request, _("The schema add successfully!"))
        return redirect('idhub:admin_schemas_import')

    def create_schema(self, file_name):
        data = self.open_file(file_name)
        try:
            json.loads(data)
        except Exception:
            messages.error(self.request, _('This is not a schema valid!'))
            return
        schema = Schemas.objects.create(file_schema=file_name, data=data)
        schema.save()
        return schema

    def open_file(self, file_name):
        data = ''
        filename = Path(settings.SCHEMAS_DIR).joinpath(file_name)
        with filename.open() as schema_file:
            data = schema_file.read()

        return data


class ImportView(ImportExport, TemplateView):
    template_name = "idhub/admin/import.html"
    subtitle = _('Import')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'dates': File_datas.objects,
        })
        return context


class ImportStep2View(ImportExport, TemplateView):
    template_name = "idhub/admin/import_step2.html"
    subtitle = _('Import')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'schemas': Schemas.objects,
        })
        return context


class ImportAddView(ImportExport, FormView):
    template_name = "idhub/admin/import_add.html"
    subtitle = _('Import')
    icon = ''
    form_class = ImportForm
    success_url = reverse_lazy('idhub:admin_import')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        cred = form.save()
        if cred:
            messages.success(self.request, _("The file import was successfully!"))
        else:
            messages.error(self.request, _("Error importing the file!"))
        return super().form_valid(form)

