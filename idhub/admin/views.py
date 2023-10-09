import logging

from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.contrib import messages
from idhub.mixins import AdminView


class AdminDashboardView(AdminView):
    template_name = "idhub/admin_dashboard.html"
    title = _('Dashboard')
    subtitle = _('Success')
    icon = 'bi bi-bell'
    section = "Home"

class People(AdminView):
    title = _("People Management")
    section = "People"


class AccessControl(AdminView):
    title = _("Access Control Management")
    section = "AccessControl"


class Credentials(AdminView):
    title = _("Credentials Management")
    section = "Credentials"


class Schemes(AdminView):
    title = _("Schemes Management")
    section = "Schemes"


class ImportExport(AdminView):
    title = _("Massive Data Management")
    section = "ImportExport"


class AdminPeopleView(People):
    template_name = "idhub/admin_people.html"
    subtitle = _('People list')
    icon = 'bi bi-person'


class AdminPeopleRegisterView(People):
    template_name = "idhub/admin_people_register.html"
    subtitle = _('People Register')
    icon = 'bi bi-person'


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
