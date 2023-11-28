import logging

from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import (
    UpdateView,
    CreateView,
    DeleteView,
    FormView
)
from django.views.generic.base import TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib import messages
from idhub.user.forms import (
    ProfileForm,
    RequestCredentialForm,
    CredentialPresentationForm,
    DemandAuthorizationForm
)
from idhub.mixins import UserView
from idhub.models import DID, VerificableCredential, Event


class MyProfile(UserView):
    title = _("My profile")
    section = "MyProfile"


class MyWallet(UserView):
    title = _("My wallet")
    section = "MyWallet"


class DashboardView(UserView, TemplateView):
    template_name = "idhub/user/dashboard.html"
    title = _('Dashboard')
    subtitle = _('Events')
    icon = 'bi bi-bell'
    section = "Home"


class ProfileView(MyProfile, UpdateView):
    template_name = "idhub/user/profile.html"
    subtitle = _('My personal data')
    icon = 'bi bi-person-gear'
    from_class = ProfileForm
    fields = ('first_name', 'last_name', 'email')
    success_url = reverse_lazy('idhub:user_profile')

    def get_object(self):
        return self.request.user

    def get_form(self):
        form = super().get_form()
        form.fields['first_name'].disabled = True
        form.fields['last_name'].disabled = True
        form.fields['email'].disabled = True
        return form

    def form_valid(self, form):
        return super().form_valid(form)


class RolesView(MyProfile, TemplateView):
    template_name = "idhub/user/roles.html"
    subtitle = _('My roles')
    icon = 'fa-brands fa-critical-role'


class GDPRView(MyProfile, TemplateView):
    template_name = "idhub/user/gdpr.html"
    subtitle = _('GDPR info')
    icon = 'bi bi-file-earmark-medical'


class CredentialsView(MyWallet, TemplateView):
    template_name = "idhub/user/credentials.html"
    subtitle = _('Credential management')
    icon = 'bi bi-patch-check-fill'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'credentials': VerificableCredential.objects,
        })
        return context


class CredentialView(MyWallet, TemplateView):
    template_name = "idhub/user/credential.html"
    subtitle = _('Credential')
    icon = 'bi bi-patch-check-fill'

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            pk=self.pk,
            user=self.request.user
        )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'object': self.object,
        })
        return context


class CredentialJsonView(MyWallet, TemplateView):

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
            user=self.request.user
        )
        response = HttpResponse(self.object.data, content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename={}'.format("credential.json")
        return response


class CredentialsRequestView(MyWallet, FormView):
    template_name = "idhub/user/credentials_request.html"
    subtitle = _('Credential request')
    icon = 'bi bi-patch-check-fill'
    form_class = RequestCredentialForm
    success_url = reverse_lazy('idhub:user_credentials')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        cred = form.save()
        if cred:
            messages.success(self.request, _("The credential was issued successfully!"))
            Event.set_EV_CREDENTIAL_ISSUED_FOR_USER(cred)
            Event.set_EV_CREDENTIAL_ISSUED(cred)
        else:
            messages.error(self.request, _("The credential does not exist!"))
        return super().form_valid(form)


class DemandAuthorizationView(MyWallet, FormView):
    template_name = "idhub/user/credentials_presentation.html"
    subtitle = _('Credential presentation')
    icon = 'bi bi-patch-check-fill'
    form_class = DemandAuthorizationForm
    success_url = reverse_lazy('idhub:user_demand_authorization')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        authorization = form.save()
        if authorization:
            if authorization.get('redirect_uri'):
                redirect(authorization.get('redirect_uri'))
        else:
            messages.error(self.request, _("Error sending credential!"))
        return super().form_valid(form)

    
class CredentialsPresentationView(MyWallet, FormView):
    template_name = "idhub/user/credentials_presentation.html"
    subtitle = _('Credential presentation')
    icon = 'bi bi-patch-check-fill'
    form_class = CredentialPresentationForm
    success_url = reverse_lazy('idhub:user_credentials')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['authorize'] = self.request.GET.params.get("uri")
        return kwargs
    
    def form_valid(self, form):
        cred = form.save()
        if cred:
            Event.set_EV_CREDENTIAL_PRESENTED_BY_USER(cred, form.org)
            Event.set_EV_CREDENTIAL_PRESENTED(cred, form.org)
            messages.success(self.request, _("The credential was presented successfully!"))
        else:
            messages.error(self.request, _("Error sending credential!"))
        return super().form_valid(form)

    
class DidsView(MyWallet, TemplateView):
    template_name = "idhub/user/dids.html"
    subtitle = _('Identities (DIDs)')
    icon = 'bi bi-patch-check-fill'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'dids': self.request.user.dids,
        })
        return context


class DidRegisterView(MyWallet, CreateView):
    template_name = "idhub/user/did_register.html"
    subtitle = _('Add a new Identity (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('label',)
    success_url = reverse_lazy('idhub:user_dids')
    object = None

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.set_did()
        form.save()
        messages.success(self.request, _('DID created successfully'))

        Event.set_EV_DID_CREATED(form.instance)
        Event.set_EV_DID_CREATED_BY_USER(form.instance)
        return super().form_valid(form)


class DidEditView(MyWallet, UpdateView):
    template_name = "idhub/user/did_register.html"
    subtitle = _('Identities (DIDs)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('label',)
    success_url = reverse_lazy('idhub:user_dids')

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, _('DID updated successfully'))
        return super().form_valid(form)


class DidDeleteView(MyWallet, DeleteView):
    subtitle = _('Identities (DIDs)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    success_url = reverse_lazy('idhub:user_dids')

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        Event.set_EV_DID_DELETED(self.object)
        self.object.delete()
        messages.success(self.request, _('DID delete successfully'))

        return redirect(self.success_url)

