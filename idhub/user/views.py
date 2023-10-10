import logging

from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.contrib import messages
from idhub.mixins import UserView


class MyProfile(UserView):
    title = _("My profile")
    section = "MyProfile"


class MyWallet(UserView):
    title = _("My Wallet")
    section = "MyWallet"


class UserDashboardView(UserView):
    template_name = "idhub/user_dashboard.html"
    title = _('Dashboard')
    subtitle = _('Success')
    icon = 'bi bi-bell'
    section = "Home"


class UserProfileView(MyProfile):
    template_name = "idhub/user_profile.html"
    subtitle = _('My personal Data')
    icon = 'bi bi-person'


class UserRolesView(MyProfile):
    template_name = "idhub/user_roles.html"
    subtitle = _('My roles')
    icon = 'fa-brands fa-critical-role'


class UserGDPRView(MyProfile):
    template_name = "idhub/user_gdpr.html"
    subtitle = _('GDPR info')
    icon = 'bi bi-file-earmark-medical'


class UserIdentitiesView(MyWallet):
    template_name = "idhub/user_identities.html"
    subtitle = _('Identities (DID)')
    icon = 'bi bi-patch-check-fill'


class UserCredentialsView(MyWallet):
    template_name = "idhub/user_credentials.html"
    subtitle = _('Credentials')
    icon = 'bi bi-patch-check-fill'


class UserCredentialsRequiredView(MyWallet):
    template_name = "idhub/user_credentials_required.html"
    subtitle = _('Credentials required')
    icon = 'bi bi-patch-check-fill'


class UserCredentialsPresentationView(MyWallet):
    template_name = "idhub/user_credentials_presentation.html"
    subtitle = _('Credentials Presentation')
    icon = 'bi bi-patch-check-fill'
