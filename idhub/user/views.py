import os
import json
import base64
import qrcode
import logging
import datetime
import weasyprint
import qrcode.image.svg

from io import BytesIO
from pathlib import Path
from pyhanko.sign import fields, signers
from pyhanko import stamp
from pyhanko.pdf_utils import text
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from django.utils.translation import gettext_lazy as _
from django.views.generic import View
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
from django_tables2 import SingleTableView
from idhub.user.tables import (
        DashboardTable,
        PersonalInfoTable,
        RolesTable,
        DIDTable,
        CredentialsTable
)
from django.core.cache import cache
from idhub.user.forms import (
    RequestCredentialForm,
    DemandAuthorizationForm,
    TermsConditionsForm
)
from utils import certs
from idhub.mixins import UserView
from idhub.models import DID, VerificableCredential, Event, Membership
from idhub_auth.models import User


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
        queryset = Event.objects.select_related('user').filter(
                user=self.request.user)

        return queryset


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
                user=self.request.user)

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
    title = _("Comunication with admin")
    subtitle = _('Service temporary close')
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
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'object': self.object,
        })
        return context


class CredentialPdfView(MyWallet, TemplateView):
    template_name = "certificates/4_Model_Certificat.html"
    subtitle = _('Credential management')
    icon = 'bi bi-patch-check-fill'
    file_name = "certificate.pdf"

    def get(self, request, *args, **kwargs):
        if not self.admin_validated:
            return redirect(reverse_lazy('idhub:user_dashboard'))
        pk = kwargs['pk']
        self.user = self.request.user
        self.object = get_object_or_404(
            VerificableCredential,
            pk=pk,
            eidas1_did__isnull=False,
            user=self.request.user
        )
        self.url_id = "{}://{}/public/credentials/{}".format(
            self.request.scheme,
            self.request.get_host(),
            self.object.hash
        )

        data = self.build_certificate()
        if self.object.eidas1_did:
            doc = self.insert_signature(data)
        else:
            doc = data
        response = HttpResponse(doc, content_type="application/pdf")
        response['Content-Disposition'] = 'attachment; filename={}'.format(self.file_name)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        this_folder = str(Path.cwd())
        path_img_sig = "idhub/static/images/4_Model_Certificat_html_58d7f7eeb828cf29.jpg"
        img_signature = next(Path.cwd().glob(path_img_sig))
        with open(img_signature, 'rb') as _f:
            img_sig = base64.b64encode(_f.read()).decode('utf-8')

        path_img_head = "idhub/static/images/4_Model_Certificat_html_7a0214c6fc8f2309.jpg"
        img_header= next(Path.cwd().glob(path_img_head))
        with open(img_header, 'rb') as _f:
            img_head = base64.b64encode(_f.read()).decode('utf-8')

        qr = self.generate_qr_code(self.url_id)

        first_name = self.user.first_name and self.user.first_name.upper() or ""
        last_name = self.user.first_name and self.user.last_name.upper() or ""
        document_id = "0000000-L"
        course = "COURSE 1"
        address = "ADDRESS"
        date_course = datetime.datetime.now()
        n_hours = 40
        n_lections = 5
        issue_date = datetime.datetime.now()
        context.update({
            'object': self.object,
            "image_signature": img_sig,
            "image_header": img_head,
            "first_name": first_name,
            "last_name": last_name,
            "document_id": document_id,
            "course": course,
            "address": address,
            "date_course": date_course,
            "n_hours": n_hours,
            "n_lections": n_lections,
            "issue_date": issue_date,
            "qr": qr
        })
        return context

    def build_certificate(self):
        doc = self.render_to_response(context=self.get_context_data())
        doc.render()
        pdf = weasyprint.HTML(string=doc.content)
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
                'Signature', box=(150, 100, 450, 150)
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

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if not self.admin_validated:
            return redirect(reverse_lazy('idhub:user_dashboard'))
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['lang'] = self.request.LANGUAGE_CODE
        domain = "{}://{}".format(self.request.scheme, self.request.get_host())
        kwargs['domain'] = domain
        return kwargs
    
    def form_valid(self, form):
        cred = form.save()
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
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

