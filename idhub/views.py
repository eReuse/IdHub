import base64
import json
import uuid
import logging
import zlib

import pyroaring
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.contrib.auth import views as auth_views
from django.contrib.auth import login as auth_login
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse, Http404

from idhub.models import DID, VerificableCredential
from idhub.email.views import NotifyActivateUserByEmail


logger = logging.getLogger(__name__)


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
        if not self.request.user.is_anonymous:
            if self.request.user.is_admin:
                return redirect(reverse_lazy('idhub:admin_dashboard'))
            else:
                return redirect(reverse_lazy('idhub:user_dashboard'))
            
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        auth_login(self.request, user)

        if user.is_anonymous:
            return redirect(reverse_lazy("idhub:login"))

        if user.is_admin:
            if settings.ENABLE_2FACTOR_AUTH:
                self.request.session["2fauth"] = str(uuid.uuid4())
                return redirect(reverse_lazy('idhub:confirm_send_2f'))

            admin_dashboard = reverse_lazy('idhub:admin_dashboard')
            self.extra_context['success_url'] = admin_dashboard

        return redirect(self.extra_context['success_url'])


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('idhub:password_reset_complete')

    def form_valid(self, form):
        password = form.cleaned_data.get("new_password1")
        user = form.user
        user.set_password(password)
        user.set_encrypted_sensitive_data(password)
        user.save()
        return HttpResponseRedirect(self.success_url)


class PasswordResetView(auth_views.PasswordResetView):
    template_name = 'auth/password_reset.html'
    email_template_name = 'auth/password_reset_email.txt'
    html_email_template_name = 'auth/password_reset_email.html'
    subject_template_name = 'auth/password_reset_subject.txt'
    success_url = reverse_lazy('idhub:password_reset_done')

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception as err:
            logger.error(err)
        # url_error = reverse_lazy('idhub:password_reset_error')
        # return HttpResponseRedirect(url_error)
        return HttpResponseRedirect(self.success_url)


def serve_did(request, did_id):
    import urllib.parse
    domain = urllib.parse.urlencode({"domain": settings.DOMAIN})[7:]
    id_did = f'did:web:{domain}:did-registry:{did_id}'
    did = get_object_or_404(DID, did=id_did)
    # Deserialize the base DID from JSON storage
    document = json.loads(did.didweb_document)
    # Has this DID issued any Verifiable Credentials? If so, we need to add a Revocation List "service"
    #  entry to the DID document.
    revoked_credentials = did.vcredentials.filter(status=VerificableCredential.Status.REVOKED)
    revoked_credential_indexes = []
    for credential in revoked_credentials:
        revoked_credential_indexes.append(credential.id)
        # revoked_credential_indexes.append(credential.revocationBitmapIndex)
    # TODO: Conditionally add "service" to DID document only if the DID has issued any VC
    revocation_bitmap = pyroaring.BitMap(revoked_credential_indexes)
    encoded_revocation_bitmap = base64.b64encode(
        zlib.compress(
            revocation_bitmap.serialize()
        )
    ).decode('utf-8')
    revocation_service = [{  # This is an object within a list.
        "id": f"{id_did}#revocation",
        "type": "RevocationBitmap2022",
        "serviceEndpoint": f"data:application/octet-stream;base64,{encoded_revocation_bitmap}"
    }]
    document["service"] = revocation_service
    # Serialize the DID + Revocation list in preparation for sending
    document = json.dumps(document)
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


