import base64
import json
import uuid
import logging
import zlib

import pyroaring
from django.db.models import Q
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.contrib.auth import views as auth_views
from django.contrib.auth import login as auth_login
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse, Http404

from idhub.models import DID, VerificableCredential, Schemas, Context, ContextFile
from idhub.email.views import NotifyActivateUserByEmail
from oidc4vp.models import Organization


logger = logging.getLogger(__name__)


class LoginView(auth_views.LoginView):
    try:
        org = Organization.objects.filter(main=True).first()
    except Exception:
        org= ""

    template_name = 'auth/login.html'
    extra_context = {
        'title': _('Login'),
        'commit_id': settings.COMMIT,
        'org': org,
    }

    def get(self, request, *args, **kwargs):
        if not self.request.user.is_anonymous:
            if self.request.user.is_admin:
                return redirect(reverse_lazy('idhub:admin_dashboard'))
            else:
                return redirect(reverse_lazy('idhub:user_dashboard'))

        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        auth_login(self.request, user)

        next_url = self.request.POST.get('next')
        if next_url:
            return redirect(next_url)

        if user.is_anonymous:
            return redirect(reverse_lazy("idhub:login"))

        if user.is_admin:
            if settings.ENABLE_2FACTOR_AUTH:
                self.request.session["2fauth"] = str(uuid.uuid4())
                return redirect(reverse_lazy('idhub:confirm_send_2f'))

            return redirect(reverse_lazy('idhub:admin_dashboard'))

        # is user
        return redirect(reverse_lazy('idhub:user_dashboard'))


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('idhub:password_reset_complete')

    def form_valid(self, form):
        password = form.cleaned_data.get("new_password1")
        user = form.user
        user.set_password(password)
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


def ServeDidRegistryView(request, did_id):
    domain = settings.DOMAIN
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

    if did.is_product:
        revocation_service.append({
            "id": f"{id_did}#product",
            "type": "ProductPassport",
            "serviceEndpoint": did.service_endpoint
        })

    document["service"] = revocation_service
    # Serialize the DID + Revocation list in preparation for sending
    document = json.dumps(document)
    retval = HttpResponse(document)
    retval.headers["Content-Type"] = "application/json"
    return retval


def ServeDidView(request, did_id):
    domain = settings.DOMAIN
    id_did = f'did:web:{domain}:{did_id}'
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


class AvailableDidView(LoginRequiredMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        did_id = kwargs['did_id']
        if self.request.user.is_admin:
            self.object = DID.objects.filter(did=did_id).filter(
                Q(user=self.request.user) | Q(user__isnull=True)
            ).first()

            if not self.object:
                 raise Http404
        else:
            self.object = get_object_or_404(
                DID,
                did=did_id,
                user=self.request.user
            )

        if self.object.is_web:
            if not self.object.available:
                if self.object.check_remote_did():
                    self.object.available = True
                    self.object.save()
                else:
                    return self.get_did()

            return redirect(self.object.get_path())

        raise Http404

    def get_did(self):
        response = HttpResponse(self.object.didweb_document, content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename={}'.format("did.json")
        return response


def SchemaView(request, file_name):
    schema = get_object_or_404(Schemas, file_schema=file_name)
    retval = HttpResponse(schema.data)
    retval.headers["Content-Type"] = "application/json"
    return retval


def ContextView(request):
    ctx = Context.get_context()
    retval = HttpResponse(ctx)
    retval.headers["Content-Type"] = "application/json"
    return retval


def ContextFileView(request, file_name):
    context = get_object_or_404(ContextFile, file_name=file_name)
    retval = HttpResponse(context.data)
    retval.headers["Content-Type"] = "application/json"
    return retval
