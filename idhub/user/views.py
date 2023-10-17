import logging

from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import UpdateView
from django.views.generic.base import TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from idhub.user.forms import ProfileForm
from idhub.mixins import UserView


class MyProfile(UserView):
    title = _("My profile")
    section = "MyProfile"


class MyWallet(UserView, TemplateView):
    title = _("My Wallet")
    section = "MyWallet"


class UserDashboardView(UserView, TemplateView):
    template_name = "idhub/user/dashboard.html"
    title = _('Dashboard')
    subtitle = _('Success')
    icon = 'bi bi-bell'
    section = "Home"


class UserProfileView(MyProfile, UpdateView):
    template_name = "idhub/user/profile.html"
    subtitle = _('My personal Data')
    icon = 'bi bi-person'
    from_class = ProfileForm
    fields = ('first_name', 'last_name', 'email')
    success_url = reverse_lazy('idhub:user_profile')

    def get_object(self):
        return self.request.user


class UserRolesView(MyProfile, TemplateView):
    template_name = "idhub/user/roles.html"
    subtitle = _('My roles')
    icon = 'fa-brands fa-critical-role'


class UserGDPRView(MyProfile, TemplateView):
    template_name = "idhub/user/gdpr.html"
    subtitle = _('GDPR info')
    icon = 'bi bi-file-earmark-medical'


class UserIdentitiesView(MyWallet):
    template_name = "idhub/user/identities.html"
    subtitle = _('Identities (DID)')
    icon = 'bi bi-patch-check-fill'


class UserCredentialsView(MyWallet):
    template_name = "idhub/user/credentials.html"
    subtitle = _('Credentials')
    icon = 'bi bi-patch-check-fill'


class UserCredentialsRequiredView(MyWallet):
    template_name = "idhub/user/credentials_required.html"
    subtitle = _('Credentials required')
    icon = 'bi bi-patch-check-fill'


class UserCredentialsPresentationView(MyWallet):
    template_name = "idhub/user/credentials_presentation.html"
    subtitle = _('Credentials Presentation')
    icon = 'bi bi-patch-check-fill'
