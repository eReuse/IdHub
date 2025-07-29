import json
import base64
import qrcode
import logging
import weasyprint
import qrcode.image.svg

from io import BytesIO
from pathlib import Path
from pyhanko.sign import fields, signers
from pyhanko import stamp
from pyhanko.pdf_utils import text
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.views.generic import View
from django.views.generic.edit import (
    UpdateView,
    CreateView,
    DeleteView,
    FormView
)
from django.template import RequestContext, Template
from django.views.generic.base import TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.core.cache import cache
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.contrib import messages
from django_tables2 import SingleTableView
from idhub.user.tables import (
        DashboardTable,
        PersonalInfoTable,
        RolesTable,
        DIDTable,
        CredentialsTable
)
from idhub.user.forms import (
    RequestCredentialForm,
    DemandAuthorizationForm,
    TermsConditionsForm
)
from utils import certs
from idhub.mixins import UserView
from idhub.models import DID, VerificableCredential, Event, Membership
from idhub_auth.models import User


logger = logging.getLogger(__name__)


class MyProfile(UserView):
    title = _("My profile")
    section = "MyProfile"


class MyWallet(UserView):
    title = _("My wallet")
    section = "MyWallet"


class DashboardView(UserView, SingleTableView):
    template_name = "idhub/user/dashboard.html"
    table_class = DashboardTable
    title = _('Dashboard')
    subtitle = _('Events')
    icon = 'bi bi-bell'
    section = "Home"

    def get_queryset(self, **kwargs):
        events_for_users = self.get_user_events()
        queryset = Event.objects.select_related('user').filter(
                user=self.request.user).filter(
                    type__in=events_for_users).order_by("-created")

        return queryset

    def get_user_events(self):
        events_for_users = [
            Event.Types.EV_USR_WELCOME,  # User welcomed
            Event.Types.EV_USR_UPDATED,  # Your data updated by admin
            Event.Types.EV_DID_CREATED,  # DID created
            Event.Types.EV_DID_DELETED,  # DID deleted
            Event.Types.EV_CREDENTIAL_DELETED,  # Credential deleted
            Event.Types.EV_CREDENTIAL_ISSUED,  # Credential issued
            Event.Types.EV_CREDENTIAL_PRESENTED,  # Credential presented
            Event.Types.EV_CREDENTIAL_CAN_BE_REQUESTED,  # Credential available
            Event.Types.EV_CREDENTIAL_REVOKED,  # Credential revoked
            Event.Types.EV_USR_SEND_VP,  # User send verificable presentation
        ]
        return events_for_users


class ProfileView(MyProfile, UpdateView, SingleTableView):
    template_name = "idhub/user/profile.html"
    table_class = PersonalInfoTable
    subtitle = _('My personal data')
    icon = 'bi bi-person-gear'
    fields = ('first_name', 'last_name', 'email')
    success_url = reverse_lazy('idhub:user_profile')
    model = User

    def get_queryset(self, **kwargs):
        queryset = Membership.objects.select_related('user').filter(
                user=self.request.user)

        return queryset

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'lang': self.request.LANGUAGE_CODE,
        })
        return context


class RolesView(MyProfile, SingleTableView):
    template_name = "idhub/user/roles.html"
    table_class = RolesTable
    subtitle = _('My roles')
    icon = 'fa-brands fa-critical-role'

    def get_queryset(self, **kwargs):
        queryset = self.request.user.roles.all()

        return queryset


class GDPRView(MyProfile, TemplateView):
    template_name = "idhub/user/gdpr.html"
    subtitle = _('Data protection')
    icon = 'bi bi-file-earmark-medical'


class CredentialsView(MyWallet, SingleTableView):
    template_name = "idhub/user/credentials.html"
    table_class = CredentialsTable
    subtitle = _('Credential management')
    icon = 'bi bi-patch-check-fill'

    def get_queryset(self):
        queryset = VerificableCredential.objects.filter(
                user=self.request.user).order_by('-created_on')

        return queryset


class TermsAndConditionsView(UserView, FormView):
    template_name = "idhub/user/terms_conditions.html"
    title = _("Data Protection")
    section = ""
    subtitle = _('Terms and Conditions')
    icon = 'bi bi-file-earmark-medical'
    form_class = TermsConditionsForm
    success_url = reverse_lazy('idhub:user_dashboard')

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


class WaitingView(UserView, TemplateView):
    template_name = "idhub/user/waiting.html"
    title = _("Comunication with admin required")
    subtitle = _('Service temporarily closed')
    section = ""
    icon = 'bi bi-file-earmark-medical'
    success_url = reverse_lazy('idhub:user_dashboard')

    def get(self, request, *args, **kwargs):
        if cache.get("KEY_DIDS"):
            return redirect(self.success_url)
        return super().get(request, *args, **kwargs)



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
        self.subtitle += ": {}".format(self.object.type)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        url_pdf = reverse_lazy('idhub:user_credential_pdf', args=[self.object.id])

        API_DLT_URL = ''
        API_DLT_TOKEN = ''

        did = self.object.subject_did
        if did and did.type == DID.Types.WEBETH:
            key_material = json.loads(did.get_key_material())
            API_DLT_URL = settings.API_DLT_URL
            API_DLT_TOKEN = key_material.get('eth_api_token', 'error')

        context.update({
            'object': self.object,
            'url_pdf': url_pdf,
            'API_DLT_URL': API_DLT_URL,
            'API_DLT_TOKEN': API_DLT_TOKEN,
        })
        return context


class CredentialPdfView(MyWallet, TemplateView):
    template_name = "certificates/{}.html"
    subtitle = _('Credential management')
    icon = 'bi bi-patch-check-fill'
    file_name = "certificate.pdf"

    def get(self, request, *args, **kwargs):
        if not cache.get("KEY_DIDS"):
            return redirect(reverse_lazy('idhub:user_dashboard'))
        pk = kwargs['pk']
        self.user = self.request.user
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
            eidas1_did__isnull=False,
            template_pdf__isnull=False,
            user=self.request.user
        )
        self.credential_type = self.object.schema.file_schema.split(".json")[0]
        self.template_name = self.template_name.format(self.credential_type)
        self.url_id = "{}://{}/public/credentials/{}".format(
            self.request.scheme,
            self.request.get_host(),
            self.object.hash
        )

        try:
            data = self.build_certificate()
            data = self.insert_signature(data)
        except Exception:
            messages.error(self.request, _("Error rendering this credencial"))
            url_success = reverse_lazy('idhub:user_credential', args=[self.object.id,])
            return redirect(url_success)

        doc = data

        response = HttpResponse(doc, content_type="application/pdf")
        response['Content-Disposition'] = 'attachment; filename={}'.format(self.file_name)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # get the excel datas
        context.update(json.loads(self.object.csv_data))
        # get the credentialSubject datas
        context.update(dict(self.object.get_datas()))

        qr = self.generate_qr_code(self.url_id)
        issue_date = context.get('certificationDate', '')
        membership_since = context.get('membershipSince', '')
        membership_type = context.get('membershipType', '').lower()

        context.update({
            'object': self.object,
            "issue_date": issue_date,
            "membership_since": membership_since,
            "membership_type": membership_type,
            "qr": qr,
        })
        return RequestContext(self.request, context)

    def build_certificate(self):
        template_pdf = self.object.template_pdf.data.read().decode()
        doc = Template(template_pdf).render(self.get_context_data())
        pdf = weasyprint.HTML(string=doc)
        return pdf.write_pdf()

    def generate_qr_code(self, data):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img_buffer = BytesIO()
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(img_buffer, format="PNG")

        return base64.b64encode(img_buffer.getvalue()).decode('utf-8')

    def get_pfx_data(self):
        did = self.object.eidas1_did
        if not did:
            return None, None
        key_material = json.loads(did.get_key_material())
        cert = key_material.get("cert")
        passphrase = key_material.get("passphrase")
        if cert and passphrase:
            return base64.b64decode(cert), passphrase.encode('utf-8')
        return None, None


    def signer_init(self):
        pfx_data, passphrase = self.get_pfx_data()
        if not pfx_data or not passphrase:
            return
        s = certs.load_cert(
            pfx_data, passphrase
        )
        return s

    def insert_signature(self, doc):
        sig = self.signer_init()
        if not sig:
            return

        _buffer = BytesIO()
        _buffer.write(doc)
        w = IncrementalPdfFileWriter(_buffer)
        fields.append_signature_field(
            w, sig_field_spec=fields.SigFieldSpec(
                'Signature', box=(150, 75, 450, 100)
            )
        )

        meta = signers.PdfSignatureMetadata(field_name='Signature')
        pdf_signer = signers.PdfSigner(
            meta, signer=sig, stamp_style=stamp.TextStampStyle(
                stamp_text='Signed by: %(signer)s\nTime: %(ts)s\nURL: %(url)s',
                text_box_style=text.TextBoxStyle()
            )
        )
        _bf_out = BytesIO()
        pdf_signer.sign_pdf(w, output=_bf_out, appearance_text_params={'url': self.url_id})
        return _bf_out.read()



class CredentialJsonView(MyWallet, TemplateView):

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
            user=self.request.user
        )
        data = self.object.get_data()
        response = HttpResponse(data, content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename={}'.format("credential.json")
        return response


class PublicCredentialJsonView(View):

    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        self.object = get_object_or_404(
            VerificableCredential,
            hash=pk,
            eidas1_did__isnull=False,
        )
        response = HttpResponse(self.object.get_data(), content_type="application/json")
        response['Content-Disposition'] = 'attachment; filename={}'.format("credential.json")
        return response


class CredentialsRequestView(MyWallet, FormView):
    template_name = "idhub/user/credentials_request.html"
    subtitle = _('Credential request')
    icon = 'bi bi-patch-check-fill'
    form_class = RequestCredentialForm
    success_url = reverse_lazy('idhub:user_credentials')

    def get(self, *args, **kwargs):
        response = super().get(*args, **kwargs)
        if not DID.objects.filter(user=self.request.user).exists():
            return redirect(reverse_lazy('idhub:user_dids_new'))

        return response


    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.if_credentials = VerificableCredential.objects.filter(
            user=self.request.user,
            status=VerificableCredential.Status.ENABLED.value,
        ).exists()

        kwargs['user'] = self.request.user
        kwargs['lang'] = self.request.LANGUAGE_CODE
        domain = "https://{}".format(self.request.get_host())
        kwargs['domain'] = domain
        kwargs['if_credentials'] = self.if_credentials
        return kwargs

    def form_valid(self, form):
        try:
            cred = form.save()
        except Exception as err:
            logger.error(err)
            messages.error(self.request, err)
            return redirect(self.success_url)

        if cred:
            messages.success(self.request, _("The credential was issued successfully!"))
            Event.set_EV_CREDENTIAL_ISSUED_FOR_USER(cred)
            Event.set_EV_CREDENTIAL_ISSUED(cred)
            url = self.request.session.pop('next_url', None)
            if url:
                return redirect(url)
        else:
            messages.error(self.request, _("The credential does not exist!"))
        return super().form_valid(form)


class DemandAuthorizationView(MyWallet, FormView):
    template_name = "idhub/user/credentials_presentation.html"
    subtitle = _('Credential presentation')
    icon = 'bi bi-patch-check-fill'
    form_class = DemandAuthorizationForm
    success_url = reverse_lazy('idhub:user_demand_authorization')

    def get(self, *args, **kwargs):
        response = super().get(*args, **kwargs)
        creds_enable = VerificableCredential.objects.filter(
            user=self.request.user,
            status=VerificableCredential.Status.ENABLED.value,
        ).exists()

        if not self.if_credentials and creds_enable:
            return redirect(reverse_lazy('idhub:user_credentials_request'))
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.if_credentials = VerificableCredential.objects.filter(
            user=self.request.user,
            status=VerificableCredential.Status.ISSUED.value,
        ).exists()

        kwargs['user'] = self.request.user
        kwargs['if_credentials'] = self.if_credentials
        return kwargs

    def form_valid(self, form):
        try:
            authorization = form.save()
        except Exception:
            txt = _("Problems connecting with {url}").format(
                url=form.org.response_uri
            )
            messages.error(self.request, txt)
            return super().form_valid(form)

        if authorization:
            return redirect(authorization)
        else:
            messages.error(self.request, _("Error sending credential!"))
        return super().form_valid(form)


class DidsView(MyWallet, SingleTableView):
    template_name = "idhub/user/dids.html"
    table_class = DIDTable
    subtitle = _('Identities (DIDs)')
    icon = 'bi bi-patch-check-fill'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'dids': self.request.user.dids,
        })
        return context

    def get_queryset(self, **kwargs):
        queryset = DID.objects.filter(user=self.request.user)

        return queryset


class DidRegisterView(MyWallet, CreateView):
    template_name = "idhub/user/did_register.html"
    subtitle = _('Add a new Identity (DID)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = DID
    fields = ('label', 'type')
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
        form.save()
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


class CallOracleView(MyWallet, View):
    subtitle = _('Identities (DIDs)')
    icon = 'bi bi-patch-check-fill'
    wallet = True
    model = VerificableCredential

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        Event.set_EV_USR_CRED_TO_DLT(self.object)
        try:
            self.object.call_oracle()
            messages.success(self.request, _('Credential successfully presented to DLT'))
        except Exception as err:
            logger.error(f"Credential to DLT failed. Details: {err}")
            messages.error(self.request, _('Credential could not be presented to DLT'))

        return redirect(reverse_lazy('idhub:user_credential', args=[self.object.id]))
