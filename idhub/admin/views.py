import os
import csv
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
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib import messages
from apiregiter import iota
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
    fields = ('first_name', 'last_name', 'email')
    success_url = reverse_lazy('idhub:admin_people_list')


class AdminPeopleRegisterView(NotifyActivateUserByEmail, People, CreateView):
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


class AdminPeopleMembershipRegisterView(People, CreateView):
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


class AdminPeopleMembershipEditView(People, CreateView):
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
    fields = ('name',)
    success_url = reverse_lazy('idhub:admin_roles')
    object = None

        
class AdminRolEditView(AccessControl, CreateView):
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
    fields = ('domain', 'description', 'rol')
    success_url = reverse_lazy('idhub:admin_services')
    object = None

        
class AdminServiceEditView(AccessControl, CreateView):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'credentials': VerificableCredential.objects,
        })
        return context


class AdminCredentialView(Credentials):
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


class AdminRevokeCredentialsView(Credentials):
    template_name = "idhub/admin/revoke_credentials.html"
    subtitle = _('Revoke Credentials')
    icon = ''


class AdminDidsView(Credentials):
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

class AdminDidRegisterView(Credentials, CreateView):
    template_name = "idhub/admin/did_register.html"
    subtitle = _('Add a new Organization Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('did', 'label')
    success_url = reverse_lazy('idhub:admin_dids')
    object = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {
            'did': iota.issue_did()
        }
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['did'].required = False
        form.fields['did'].disabled = True
        return form

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('DID created successfully'))
        return super().form_valid(form)


class AdminDidEditView(Credentials, UpdateView):
    template_name = "idhub/admin/did_register.html"
    subtitle = _('Organization Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('did', 'label')
    success_url = reverse_lazy('idhub:admin_dids')

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        return super().get(request, *args, **kwargs)

    def get_form(self):
        form = super().get_form()
        form.fields['did'].required = False
        form.fields['did'].disabled = True
        return form

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, _('DID updated successfully'))
        return super().form_valid(form)


class AdminDidDeleteView(Credentials, DeleteView):
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

        
class AdminSchemasDeleteView(SchemasMix):

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(Schemas, pk=self.pk)
        self.object.delete()

        return redirect('idhub:admin_schemas')


class AdminSchemasDownloadView(SchemasMix):

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(Schemas, pk=self.pk)

        response = HttpResponse(self.object.data, content_type="application/json")
        response['Content-Disposition'] = 'inline; filename={}'.format(self.object.file_schema)
        return response


class AdminSchemasNewView(SchemasMix):
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


class AdminImportView(ImportExport):
    template_name = "idhub/admin/import.html"
    subtitle = _('Import')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'dates': File_datas.objects,
        })
        return context


class AdminImportStep2View(ImportExport):
    template_name = "idhub/admin/import_step2.html"
    subtitle = _('Import')
    icon = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'schemas': Schemas.objects,
        })
        return context


class AdminImportStep3View(ImportExport):
    template_name = "idhub/admin/import_step3.html"
    subtitle = _('Import')
    icon = ''
    success_url = reverse_lazy('idhub:admin_import')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form': ImportForm(),
        })
        return context

    def post(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.schema = get_object_or_404(Schemas, pk=self.pk)
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            result = self.handle_uploaded_file()
            if not result:
                messages.error(request, _("There are some errors in the file"))
                return super().get(request, *args, **kwargs)
            return redirect(self.success_url)
        else:
            return super().get(request, *args, **kwargs)

        return super().post(request, *args, **kwargs)

    def handle_uploaded_file(self):
        f = self.request.FILES.get('file_import')
        if not f:
            messages.error(self.request, _("There aren't file"))
            return

        file_name = f.name
        if File_datas.objects.filter(file_name=file_name, success=True).exists():
            messages.error(self.request, _("This file already exists!"))
            return

        self.json_schema = json.loads(self.schema.data)
        df = pd.read_csv (f, delimiter="\t", quotechar='"', quoting=csv.QUOTE_ALL)
        data_pd = df.fillna('').to_dict()
        rows = {}

        if not data_pd:
            File_datas.objects.create(file_name=file_name, success=False)
            return

        for n in range(df.last_valid_index()+1):
            row = {}
            for k in data_pd.keys():
                row[k] = data_pd[k][n]

            user = self.validate(n, row)
            if not user:
                File_datas.objects.create(file_name=file_name, success=False)
                return

            rows[user] = row

        File_datas.objects.create(file_name=file_name)
        for k, v in rows.items():
            self.create_credential(k, v)

        return True

    def validate(self, line, row):
        try:
            validate(instance=row, schema=self.json_schema)
        except Exception as e:
            messages.error(self.request, "line {}: {}".format(line+1, e))
            return

        user = User.objects.filter(email=row.get('email'))
        if not user:
            txt = _('The user not exist!')
            messages.error(self.request, "line {}: {}".format(line+1, txt))
            return

        return user.first()

    def create_credential(self, user, row):
        d = copy.copy(self.json_schema)
        d['instance'] = row
        return VerificableCredential.objects.create(
            verified=False,
            user=user,
            data=json.dumps(d)
        )

