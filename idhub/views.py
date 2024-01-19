import uuid

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.contrib.auth import views as auth_views
from django.contrib.auth import login as auth_login
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse, Http404

from idhub.models import DID
from idhub.email.views import NotifyActivateUserByEmail
from trustchain_idhub import settings


class LoginView(auth_views.LoginView):
    template_name = 'auth/login.html'
    extra_context = {
        'title': _('Login'),
        'success_url': reverse_lazy('idhub:user_dashboard'),
    }

    def get(self, request, *args, **kwargs):
        self.extra_context['success_url'] = request.GET.get(
            'next',
            reverse_lazy('idhub:user_dashboard')
        )
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        password = form.cleaned_data.get("password")
        auth_login(self.request, user)

        sensitive_data_encryption_key = user.decrypt_sensitive_data(password)

        if not user.is_anonymous and user.is_admin:
            admin_dashboard = reverse_lazy('idhub:admin_dashboard')
            self.extra_context['success_url'] = admin_dashboard
            # encryption_key = user.encrypt_data(
            #     sensitive_data_encryption_key,
            #     settings.SECRET_KEY
            # )
            # cache.set("KEY_DIDS", encryption_key, None)
            cache.set("KEY_DIDS", sensitive_data_encryption_key, None)
            if not settings.DEVELOPMENT:
                self.request.session["2fauth"] = str(uuid.uuid4())
                return redirect(reverse_lazy('idhub:confirm_send_2f'))

        self.request.session["key_did"] = user.encrypt_data(
            sensitive_data_encryption_key,
            user.password+self.request.session._session_key
        )

        return HttpResponseRedirect(self.extra_context['success_url'])


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('idhub:password_reset_complete')

    def form_valid(self, form):
        password = form.cleaned_data.get("password")
        user = form.get_user()
        user.set_encrypted_sensitive_data(password)
        user.save()
        return HttpResponseRedirect(self.success_url)


def serve_did(request, did_id):
    id_did = f'did:web:{settings.DOMAIN}:did-registry:{did_id}'
    did = get_object_or_404(DID, did=id_did)
    document = did.didweb_document
    retval = HttpResponse(document)
    retval.headers["Content-Type"] = "application/json"
    return retval


class DobleFactorSendView(LoginRequiredMixin, NotifyActivateUserByEmail, TemplateView):
    template_name = 'auth/2fadmin.html'
    subject_template_name = 'auth/2fadmin_email_subject.txt'
    email_template_name = 'auth/2fadmin_email.txt'
    html_email_template_name = 'auth/2fadmin_email.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise Http404

        f2auth = self.request.session.get("2fauth")
        if not f2auth:
            raise Http404

        self.send_email(self.request.user, token=f2auth)
        return super().get(request, *args, **kwargs)


