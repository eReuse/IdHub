import logging

from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.views.generic.base import TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from apiregiter import iota
from idhub.user.forms import ProfileForm
from idhub.mixins import UserView
from idhub.models import DID


class MyProfile(UserView):
    title = _("My profile")
    section = "MyProfile"


class MyWallet(UserView):
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


class UserCredentialsView(MyWallet, TemplateView):
    template_name = "idhub/user/credentials.html"
    subtitle = _('Credentials')
    icon = 'bi bi-patch-check-fill'


class UserCredentialsRequiredView(MyWallet, TemplateView):
    template_name = "idhub/user/credentials_required.html"
    subtitle = _('Credentials required')
    icon = 'bi bi-patch-check-fill'


class UserCredentialsPresentationView(MyWallet, TemplateView):
    template_name = "idhub/user/credentials_presentation.html"
    subtitle = _('Credentials Presentation')
    icon = 'bi bi-patch-check-fill'

    
class UserDidsView(MyWallet, TemplateView):
    template_name = "idhub/user/dids.html"
    subtitle = _('Identities (DID)')
    icon = 'bi bi-patch-check-fill'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'dids': self.request.user.dids,
        })
        return context

class UserDidRegisterView(MyWallet, CreateView):
    template_name = "idhub/user/did_register.html"
    subtitle = _('Add a new Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('did', 'label')
    success_url = reverse_lazy('idhub:user_dids')
    object = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {
            'did': iota.issue_did(),
            'user': self.request.user
        }
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['did'].required = False
        form.fields['did'].disabled = True
        return form

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.save()
        messages.success(self.request, _('DID created successfully'))
        return super().form_valid(form)


class UserDidEditView(MyWallet, UpdateView):
    template_name = "idhub/user/did_register.html"
    subtitle = _('Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('did', 'label')
    success_url = reverse_lazy('idhub:user_dids')

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


class UserDidDeleteView(MyWallet, DeleteView):
    subtitle = _('Identities (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    success_url = reverse_lazy('idhub:user_dids')

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        self.object.delete()
        messages.success(self.request, _('DID delete successfully'))

        return redirect(self.success_url)
