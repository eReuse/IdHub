import logging

from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from idhub.models import Membership
from idhub.mixins import AdminView
from idhub.admin.forms import ProfileForm, MembershipForm


class AdminDashboardView(AdminView, TemplateView):
    template_name = "idhub/admin_dashboard.html"
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


class Schemes(AdminView, TemplateView):
    title = _("Schemes Management")
    section = "Schemes"


class ImportExport(AdminView, TemplateView):
    title = _("Massive Data Management")
    section = "ImportExport"


class AdminPeopleListView(People, TemplateView):
    template_name = "idhub/admin_people.html"
    subtitle = _('People list')
    icon = 'bi bi-person'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'users': User.objects.filter(),
        })
        return context


class AdminPeopleView(People, TemplateView):
    template_name = "idhub/admin_user.html"
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
    template_name = "idhub/admin_user_edit.html"
    from_class = ProfileForm
    fields = ('first_name', 'last_name', 'email', 'username')
    success_url = reverse_lazy('idhub:admin_people_list')


class AdminPeopleRegisterView(People, CreateView):
    template_name = "idhub/admin_people_register.html"
    subtitle = _('People Register')
    icon = 'bi bi-person'
    model = User
    from_class = ProfileForm
    fields = ('first_name', 'last_name', 'email', 'username')
    success_url = reverse_lazy('idhub:admin_people_list')

    def get_success_url(self):
        # import pdb; pdb.set_trace()
        self.success_url = reverse_lazy(
            'idhub:admin_people_membership_new',
            kwargs={"pk": self.object.id}
        )
        return self.success_url


class AdminPeopleMembershipRegisterView(People, CreateView):
    template_name = "idhub/admin_people_membership_register.html"
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
        

class AdminRolesView(AccessControl):
    template_name = "idhub/admin_roles.html"
    subtitle = _('Roles Management')
    icon = ''


class AdminServicesView(AccessControl):
    template_name = "idhub/admin_services.html"
    subtitle = _('Service Management')
    icon = ''


class AdminCredentialsView(Credentials):
    template_name = "idhub/admin_credentials.html"
    subtitle = _('Credentials list')
    icon = ''


class AdminIssueCredentialsView(Credentials):
    template_name = "idhub/admin_issue_credentials.html"
    subtitle = _('Issuance of Credentials')
    icon = ''


class AdminRevokeCredentialsView(Credentials):
    template_name = "idhub/admin_revoke_credentials.html"
    subtitle = _('Revoke Credentials')
    icon = ''


class AdminWalletIdentitiesView(Credentials):
    template_name = "idhub/admin_wallet_identities.html"
    subtitle = _('Organization Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True


class AdminWalletCredentialsView(Credentials):
    template_name = "idhub/admin_wallet_credentials.html"
    subtitle = _('Credentials')
    icon = 'bi bi-patch-check-fill'
    wallet = True


class AdminWalletConfigIssuesView(Credentials):
    template_name = "idhub/admin_wallet_issues.html"
    subtitle = _('Configure Issues')
    icon = 'bi bi-patch-check-fill'
    wallet = True


class AdminSchemesView(Schemes):
    template_name = "idhub/admin_schemes.html"
    subtitle = _('Schemes List')
    icon = ''


class AdminSchemesImportView(Schemes):
    template_name = "idhub/admin_schemes_import.html"
    subtitle = _('Import Schemes')
    icon = ''


class AdminSchemesExportView(Schemes):
    template_name = "idhub/admin_schemes_export.html"
    subtitle = _('Export Schemes')
    icon = ''


class AdminImportView(ImportExport):
    template_name = "idhub/admin_import.html"
    subtitle = _('Import')
    icon = ''


class AdminExportView(ImportExport):
    template_name = "idhub/admin_export.html"
    subtitle = _('Export')
    icon = ''
