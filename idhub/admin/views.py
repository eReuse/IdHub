import os
import json
from pathlib import Path
from smtplib import SMTPException
from django_tables2 import SingleTableView

from django.conf import settings
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView, View
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
from django.core.cache import cache
from utils import credtools
from idhub_auth.models import User
from idhub_auth.forms import ProfileForm
from idhub.mixins import AdminView, Http403
from idhub.email.views import NotifyActivateUserByEmail
from idhub.admin.forms import (
    EncryptionKeyForm,
    ImportCertificateForm,
    ImportForm,
    MembershipForm,
    TermsConditionsForm,
    SchemaForm,
    UserRolForm
)
from idhub.admin.tables import (
        DashboardTable,
        UserTable,
        RolesTable,
        ServicesTable,
        CredentialTable,
        DIDTable,
        DataTable,
        TemplateTable
)
from idhub.models import (
    DID,
    Event,
    File_datas,
    Membership,
    Rol,
    Service,
    Schemas,
    UserRol,
    VerificableCredential,
)


class TermsAndConditionsView(AdminView, FormView):
    template_name = "idhub/admin/terms_conditions.html"
    title = _('Data protection')
    section = ""
    subtitle = _('Terms and Conditions')
    icon = 'bi bi-file-earmark-medical'
    form_class = TermsConditionsForm
    success_url = reverse_lazy('idhub:admin_dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.request.user.accept_gdpr:
            kwargs['initial'] = {
                "accept_privacy": True,
                "accept_legal": True,
                "accept_cookies": True
            }
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class EncryptionKeyView(AdminView, FormView):
    template_name = "idhub/admin/encryption_key.html"
    title = _('Encryption Key')
    section = ""
    subtitle = _('Encryption Key')
    icon = 'bi bi-key'
    form_class = EncryptionKeyForm
    success_url = reverse_lazy('idhub:admin_dashboard')

    def get(self, request, *args, **kwargs):
        if cache.get("KEY_DIDS"):
            return redirect(self.success_url)

        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class DobleFactorAuthView(AdminView, View):
    url = reverse_lazy('idhub:admin_dashboard')

    def get(self, request, *args, **kwargs):
        if not self.request.user.is_admin:
            raise Http403()

        if not self.request.session.get("2fauth"):
            return redirect(self.url)
            
        if self.request.session.get("2fauth") == str(kwargs.get("admin2fauth")):
            self.request.session.pop("2fauth", None)
            return redirect(self.url)

        return redirect(reverse_lazy("idhub:login"))


class DashboardView(AdminView, SingleTableView):
    template_name = "idhub/admin/dashboard.html"
    table_class = DashboardTable
    title = _('Dashboard')
    subtitle = _('Events')
    icon = 'bi bi-bell'
    section = "Home"
    model = Event

    def get_queryset(self):
        """
        Override the get_queryset method to filter events based on the user type.
        """
        events_for_admins = self.get_admin_events()
        return Event.objects.filter(type__in=events_for_admins).order_by("-created")

    def get_admin_events(self):
        return [
            Event.Types.EV_USR_REGISTERED,  # User registered
            Event.Types.EV_USR_UPDATED_BY_ADMIN,  # User's data updated by admin
            Event.Types.EV_USR_DELETED_BY_ADMIN,  # User deactivated by admin
            Event.Types.EV_DID_CREATED_BY_USER,  # DID created by user
            Event.Types.EV_CREDENTIAL_DELETED_BY_USER,  # Credential deleted by user
            Event.Types.EV_CREDENTIAL_ISSUED_FOR_USER,  # Credential issued for user
            Event.Types.EV_CREDENTIAL_PRESENTED_BY_USER,  # Credential presented by user
            Event.Types.EV_CREDENTIAL_ENABLED,  # Credential enabled
            Event.Types.EV_CREDENTIAL_REVOKED_BY_ADMIN,  # Credential revoked by admin
            Event.Types.EV_ROLE_CREATED_BY_ADMIN,  # Role created by admin
            Event.Types.EV_ROLE_MODIFIED_BY_ADMIN,  # Role modified by admin
            Event.Types.EV_ROLE_DELETED_BY_ADMIN,  # Role deleted by admin
            Event.Types.EV_SERVICE_CREATED_BY_ADMIN,  # Service created by admin
            Event.Types.EV_SERVICE_MODIFIED_BY_ADMIN,  # Service modified by admin
            Event.Types.EV_SERVICE_DELETED_BY_ADMIN,  # Service deleted by admin
            Event.Types.EV_ORG_DID_CREATED_BY_ADMIN,  # Organisational DID created by admin
            Event.Types.EV_ORG_DID_DELETED_BY_ADMIN,  # Organisational DID deleted by admin
            Event.Types.EV_USR_DEACTIVATED_BY_ADMIN,  # User deactivated
            Event.Types.EV_DATA_UPDATE_REQUESTED,  # Data update requested. Pending approval by administrator
        ]


class People(AdminView):
    title = _("User management")
    section = "People"


class AccessControl(AdminView, TemplateView):
    title = _("Access control management")
    section = "AccessControl"


class Credentials(AdminView, TemplateView):
    title = _("Credential management")
    section = "Credential"


class SchemasMix(AdminView, TemplateView):
    title = _("Template management")
    section = "Template"


class ImportExport(AdminView):
    title = _("Data file management")
    section = "ImportExport"


class PeopleListView(People, SingleTableView):
    template_name = "idhub/admin/people.html"
    subtitle = _('View users')
    icon = 'bi bi-person'
    table_class = UserTable
    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'users': User.objects.filter(),
        })
        return context

    def get_queryset(self, **kwargs):
        queryset = super().get_queryset(**kwargs)

        return queryset


class PeopleView(People, TemplateView):
    template_name = "idhub/admin/user.html"
    subtitle = _('User personal information')
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
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        if self.object == self.request.user:
            messages.error(self.request, _('It is not possible deactivate your account!'))
            return redirect('idhub:admin_people', self.object.id)

        if self.object.is_active:
            self.object.is_active = False
            Event.set_EV_USR_DEACTIVATED_BY_ADMIN(self.object)
        else:
            self.object.is_active = True
            Event.set_EV_USR_ACTIVATED_BY_ADMIN(self.object)
        self.object.save()

        return redirect('idhub:admin_people', self.object.id)
            

class PeopleDeleteView(PeopleView):

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        if self.object != self.request.user:
            Event.set_EV_USR_DELETED_BY_ADMIN(self.object)
            self.object.delete()
        else:
            messages.error(self.request, _('It is not possible delete your account!'))

        return redirect('idhub:admin_people_list')
            

class PeopleEditView(People, FormView):
    template_name = "idhub/admin/user_edit.html"
    subtitle = _('Update user')
    icon = 'bi bi-person'
    form_class = ProfileForm
    success_url = reverse_lazy('idhub:admin_people_list')

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.user = get_object_or_404(User, pk=self.pk)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.user = get_object_or_404(User, pk=self.pk)
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'object': self.user,
        })
        return context

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, _('The account was updated successfully'))
        Event.set_EV_USR_UPDATED_BY_ADMIN(user)
        Event.set_EV_USR_UPDATED(user)

        return super().form_valid(form)


class PeopleRegisterView(NotifyActivateUserByEmail, People, CreateView):
    template_name = "idhub/admin/people_register.html"
    subtitle = _('Add user')
    icon = 'bi bi-person'
    form_class = ProfileForm
    success_url = reverse_lazy('idhub:admin_people_list')

    def get_success_url(self):
        self.success_url = reverse_lazy(
            'idhub:admin_people_membership_new',
            kwargs={"pk": self.object.id}
        )
        return self.success_url

    def form_valid(self, form):
        super().form_valid(form)
        user = form.instance
        user.set_encrypted_sensitive_data()
        user.save()
        self.create_defaults_dids(user)
        messages.success(self.request, _('The account was created successfully'))
        Event.set_EV_USR_REGISTERED(user)
        Event.set_EV_USR_WELCOME(user)

        if user.is_active:
            try:
                self.send_email(user)
            except SMTPException as e:
                messages.error(self.request, e)
        return super().form_valid(form)

    def create_defaults_dids(self, user):
        did = DID(label="Default", user=user, type=DID.Types.WEB)
        did.set_did()
        did.save()


class PeopleMembershipRegisterView(People, FormView):
    template_name = "idhub/admin/people_membership_register.html"
    subtitle = _('Associate a membership to the user')
    icon = 'bi bi-person'
    form_class = MembershipForm
    model = Membership
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
        form.fields['start_date'].required = True
        return form

    def get_form_kwargs(self):
        self.object = self.model(user=self.user)
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Membership created successfully'))
        return super().form_valid(form)

    def get_success_url(self):
        self.success_url = reverse_lazy(
            'idhub:admin_people_rol_new',
            kwargs={"pk": self.user.id}
        )
        return self.success_url


class PeopleMembershipEditView(People, FormView):
    template_name = "idhub/admin/people_membership_register.html"
    subtitle = _('Associate a membership to the user')
    icon = 'bi bi-person'
    form_class = MembershipForm
    model = Membership
    success_url = reverse_lazy('idhub:admin_people_list')

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        self.user = self.object.user
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        self.user = self.object.user
        return super().post(request, *args, **kwargs)

    def get_form(self):
        form = super().get_form()
        form.fields['start_date'].widget.input_type = 'date'
        form.fields['end_date'].widget.input_type = 'date'
        form.fields['start_date'].required = True
        return form

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Membership updated successfully'))
        return super().form_valid(form)


class PeopleMembershipDeleteView(PeopleView):
    model = Membership

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        if self.object != self.request.user:
            user = self.object.user
            self.object.delete()
        else:
            messages.error(self.request, _('Is not possible delete your account!'))

        return redirect('idhub:admin_people_edit', user.id)

        
class PeopleRolRegisterView(People, FormView):
    template_name = "idhub/admin/people_rol_register.html"
    subtitle = _('Add a user role to access a service')
    icon = 'bi bi-person'
    form_class = UserRolForm
    model = UserRol

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
        kwargs['instance'] = self.object
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Membership created successfully'))
        return super().form_valid(form)

    def get_success_url(self):
        self.success_url = reverse_lazy(
            'idhub:admin_people_edit',
            kwargs={"pk": self.user.id}
        )
        return self.success_url


class PeopleRolEditView(People, FormView):
    template_name = "idhub/admin/people_rol_register.html"
    subtitle = _('Modify a user role to access a service')
    icon = 'bi bi-person'
    form_class = UserRolForm
    model = UserRol

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Membership updated successfully'))
        return super().form_valid(form)

    def get_success_url(self):
        self.success_url = reverse_lazy(
            'idhub:admin_people_edit',
            kwargs={"pk": self.object.user.id}
        )
        return self.success_url


class PeopleRolDeleteView(PeopleView):
    model = UserRol

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        user = self.object.user

        self.object.delete()

        return redirect('idhub:admin_people_edit', user.id)


class RolesView(AccessControl, SingleTableView):
    template_name = "idhub/admin/roles.html"
    subtitle = _('Manage roles')
    table_class = RolesTable
    icon = ''
    model = Rol

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', None)
        if queryset is None:
            self.object_list = self.model.objects.all()

        return super().get_context_data(**kwargs)


class RolRegisterView(AccessControl, CreateView):
    template_name = "idhub/admin/rol_register.html"
    subtitle = _('Add role')
    icon = ''
    model = Rol
    fields = ('name', "description")
    success_url = reverse_lazy('idhub:admin_roles')
    object = None
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Role created successfully'))
        Event.set_EV_ROLE_CREATED_BY_ADMIN()
        return super().form_valid(form)

        
class RolEditView(AccessControl, UpdateView):
    template_name = "idhub/admin/rol_register.html"
    subtitle = _('Edit role')
    icon = ''
    model = Rol
    fields = ('name', "description")
    success_url = reverse_lazy('idhub:admin_roles')

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        if pk:
            self.object = get_object_or_404(self.model, pk=pk)
        kwargs = super().get_form_kwargs()
        return kwargs
        
    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Role updated successfully'))
        Event.set_EV_ROLE_MODIFIED_BY_ADMIN()
        return super().form_valid(form)


class RolDeleteView(AccessControl):
    model = Rol

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        self.object.delete()
        messages.success(self.request, _('Role deleted successfully'))
        Event.set_EV_ROLE_DELETED_BY_ADMIN()
        return redirect('idhub:admin_roles')


class ServicesView(AccessControl, SingleTableView):
    template_name = "idhub/admin/services.html"
    table_class = ServicesTable
    subtitle = _('Manage services')
    icon = ''
    model = Service

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', None)
        if queryset is None:
            self.object_list = self.model.objects.all()

        return super().get_context_data(**kwargs)


class ServiceRegisterView(AccessControl, CreateView):
    template_name = "idhub/admin/service_register.html"
    subtitle = _('Add service')
    icon = ''
    model = Service
    fields = ('domain', 'description', 'rol')
    success_url = reverse_lazy('idhub:admin_services')
    object = None

    def get_form(self):
        form = super().get_form()
        form.fields['rol'].required = False
        return form

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Service created successfully'))
        Event.set_EV_SERVICE_CREATED_BY_ADMIN()
        return super().form_valid(form)

        
class ServiceEditView(AccessControl, UpdateView):
    template_name = "idhub/admin/service_register.html"
    subtitle = _('Modify service')
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

    def get_form(self):
        form = super().get_form()
        form.fields['rol'].required = False
        return form

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Service updated successfully'))
        Event.set_EV_SERVICE_MODIFIED_BY_ADMIN()
        return super().form_valid(form)


class ServiceDeleteView(AccessControl):
    model = Service

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)

        self.object.delete()
        messages.success(self.request, _('Service deleted successfully'))
        Event.set_EV_SERVICE_DELETED_BY_ADMIN()
        return redirect('idhub:admin_services')


class CredentialsView(Credentials, SingleTableView):
    template_name = "idhub/admin/credentials.html"
    table_class = CredentialTable
    subtitle = _('View credentials')
    icon = ''
    model = VerificableCredential

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', None)
        if queryset is None:
            self.object_list = self.model.objects.all()

        return super().get_context_data(**kwargs)


class CredentialView(Credentials):
    template_name = "idhub/admin/issue_credentials.html"
    subtitle = _('Change credential status')
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
        self.check_valid_user()
        pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
        )
        response = HttpResponse(self.object.get_data(), content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename={}'.format("credential.json")
        return response


class RevokeCredentialsView(Credentials):
    success_url = reverse_lazy('idhub:admin_credentials')

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
        )
        if self.object.status == VerificableCredential.Status.ISSUED:
            self.object.status = VerificableCredential.Status.REVOKED
            self.object.save()
            messages.success(self.request, _('Credential revoked successfully'))
            Event.set_EV_CREDENTIAL_REVOKED_BY_ADMIN(self.object)
            Event.set_EV_CREDENTIAL_REVOKED(self.object)

        return redirect(self.success_url)


class DeleteCredentialsView(Credentials):
    success_url = reverse_lazy('idhub:admin_credentials')

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
        )
        self.object.delete()
        messages.success(self.request, _('Credential deleted successfully'))
        Event.set_EV_CREDENTIAL_DELETED(self.object)
        Event.set_EV_CREDENTIAL_DELETED_BY_ADMIN(self.object)

        return redirect(self.success_url)


class DidsView(Credentials, SingleTableView):
    template_name = "idhub/admin/dids.html"
    table_class = DIDTable
    subtitle = _('Manage identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', None)
        dids = DID.objects.filter(user__isnull=True)
        if queryset is None:
            self.object_list = dids.all()

        context = super().get_context_data(**kwargs)
        context.update({
            'dids': dids
        })
        return context


class DidRegisterView(Credentials, CreateView):
    template_name = "idhub/admin/did_register.html"
    subtitle = _('Add a new organizational identity (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('label', 'type')
    success_url = reverse_lazy('idhub:admin_dids')
    object = None

    def form_valid(self, form):
        form.instance.set_did()
        form.save()
        messages.success(self.request, _('DID created successfully'))
        Event.set_EV_ORG_DID_CREATED_BY_ADMIN(form.instance)
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
        form.save()
        messages.success(self.request, _('DID updated successfully'))
        return super().form_valid(form)


class DidDeleteView(Credentials, DeleteView):
    subtitle = _('Organization Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    success_url = reverse_lazy('idhub:admin_dids')

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        Event.set_EV_ORG_DID_DELETED_BY_ADMIN(self.object)
        self.object.delete()
        messages.success(self.request, _('DID delete successfully'))
        return redirect(self.success_url)


class WalletCredentialsView(Credentials):
    template_name = "idhub/admin/wallet_credentials.html"
    subtitle = _('View org. credentials')
    icon = 'bi bi-patch-check-fill'
    wallet = True


class WalletConfigIssuesView(Credentials, FormView):
    template_name = "idhub/admin/wallet_issues.html"
    subtitle = _('Configure credential issuance')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    form_class = ImportCertificateForm
    success_url = reverse_lazy('idhub:admin_dids')

    def form_valid(self, form):
        cred = form.save()
        if cred:
            messages.success(self.request, _("The credential was imported successfully!"))
            Event.set_EV_ORG_DID_CREATED_BY_ADMIN(cred)
        else:
            messages.error(self.request, _("Error importing the credential!"))
        return super().form_valid(form)


class SchemasView(SchemasMix, SingleTableView):
    template_name = "idhub/admin/schemas.html"
    table_class = TemplateTable
    subtitle = _('View credential templates')
    icon = ''
    model = Schemas

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', None)
        if queryset is None:
            self.object_list = self.model.objects.all()

        return super().get_context_data(**kwargs)


class SchemasDeleteView(SchemasMix):

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        schema.vcredentials.filter(status=VerificableCredential.Status.ISSUED).count()
        self.object = get_object_or_404(
            Schemas,
            pk=self.pk,
            vcredentials__status=VerificableCredential.Status.ISSUED
        )
        self.object.delete()

        return redirect('idhub:admin_schemas')


class SchemasDownloadView(SchemasMix):

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(Schemas, pk=self.pk)

        response = HttpResponse(self.object.data, content_type="application/json")
        response['Content-Disposition'] = 'inline; filename={}'.format(self.object.file_schema)
        return response


class SchemasNewView(SchemasMix):
    template_name = "idhub/admin/schemas_new.html"
    subtitle = _('Upload template')
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
            ldata = json.loads(data)
            assert credtools.validate_schema(ldata)
            name = ldata.get('name')
            assert name
        except Exception:
            messages.error(self.request, _('This is not a valid schema!'))
            return
        schema = Schemas.objects.create(file_schema=file_name, data=data, type=name)
        schema.save()
        return schema


class SchemasImportView(SchemasMix):
    template_name = "idhub/admin/schemas_import.html"
    subtitle = _('Import template')
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
        self.check_valid_user()
        self.file_name = kwargs['file_schema']
        schemas_files = os.listdir(settings.SCHEMAS_DIR)
        if self.file_name not in schemas_files:
            file_name = self.file_name
            messages.error(self.request, f"The schema {file_name} not exist!")
            return redirect('idhub:admin_schemas_import')

        schema = self.create_schema()
        if schema:
            messages.success(self.request, _("The schema was added sucessfully"))
        return redirect('idhub:admin_schemas')

    def create_schema(self):
        data = self.open_file()
        try:
            ldata = json.loads(data)
            assert credtools.validate_schema(ldata)
            name = ldata.get('name')
            title = ldata.get('title')
            assert name
            assert title
        except Exception:
            messages.error(self.request, _('This is not a valid schema!'))
            return

        _name = json.dumps(ldata.get('name', ''))
        _description = json.dumps(ldata.get('description', ''))

        schema = Schemas.objects.create(
            file_schema=self.file_name,
            data=data,
            type=title,
            _name=_name,
            _description=_description,
            # template_description=_description
            template_description=self.get_description()
        )
        schema.save()
        return schema

    def open_file(self):
        data = ''
        filename = Path(settings.SCHEMAS_DIR).joinpath(self.file_name)
        with filename.open() as schema_file:
            data = schema_file.read()

        return data

    def get_template_description(self):
        context = {}
        template_name = 'credentials/{}'.format(
            self.file_name
        )
        tmpl = get_template(template_name)
        return tmpl.render(context)

    def get_description(self):
        for des in json.loads(self.get_template_description()).get('description', []):
            if settings.LANGUAGE_CODE == des.get('lang'):
                return des.get('value', '')
        return ''


class ImportView(ImportExport, SingleTableView):
    template_name = "idhub/admin/import.html"
    table_class = DataTable
    subtitle = _('Imported data')
    icon = ''
    model = File_datas

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


class ImportAddView(NotifyActivateUserByEmail, ImportExport, FormView):
    template_name = "idhub/admin/import_add.html"
    subtitle = _('Import')
    icon = ''
    form_class = ImportForm
    success_url = reverse_lazy('idhub:admin_import')

    def form_valid(self, form):
        creds = form.save()
        if creds:
            messages.success(self.request, _("The file was imported successfully!"))
            for cred in creds:
                Event.set_EV_CREDENTIAL_ENABLED(cred)
                Event.set_EV_CREDENTIAL_CAN_BE_REQUESTED(cred)
        else:
            messages.error(self.request, _("Error importing the file!"))

        for user in form.users:
            try:
                self.send_email(user)
            except SMTPException as e:
                messages.error(self.request, e.message)

        return super().form_valid(form)
