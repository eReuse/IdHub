import base64
import json
import uuid
import logging
import zlib
import jwt
import requests

import pyroaring
from django.db.models import Q
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic import FormView
from django.contrib.auth import views as auth_views
from django.contrib.auth import login as auth_login
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse, Http404, JsonResponse
from jwt.algorithms import get_default_algorithms

from idhub.models import DID, VerificableCredential, Schemas, Context, ContextFile
from idhub.email.views import NotifyActivateUserByEmail
from oidc4vp.models import Organization
from .forms import VerificationForm

from pyvckit.verify import verify_schema, verify_signature, resolve_did


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

    if did.is_product and did.service_endpoint:
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

    if not did_id or did_id == ".well-known":
        id_did = f'did:web:{domain}'
    else:
        did_path = did_id.replace("/", ":")
        id_did = f'did:web:{domain}:{did_path}'

    did = get_object_or_404(DID, did=id_did)

    if not did.didweb_document:
        if did.key_material:
            try:
                document = did.get_did_document()
            except Exception as e:
                return JsonResponse({"error": "DID keys exist but document generation failed."}, status=500)
        else:
            return JsonResponse({"error": "DID exists but no document or keys have been generated."}, status=404)
    else:
        try:
            document = json.loads(did.didweb_document)
        except json.JSONDecodeError:
            return JsonResponse({"error": "DID Document in database is corrupt or invalid JSON."}, status=500)


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

    if did.is_product and did.service_endpoint:
        revocation_service.append({
            "id": f"{id_did}#product",
            "type": "ProductPassport",
            "serviceEndpoint": did.service_endpoint
        })

    document["service"] = revocation_service
    # Serialize the DID + Revocation list in preparation for sending
    document = json.dumps(document)
    retval = HttpResponse(document)
    retval.headers["Content-Type"] = "application/did+ld+json"
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


class PublicVerificationView(FormView):
    template_name = 'idhub/verification_portal.html'
    form_class = VerificationForm

    def form_valid(self, form):
        upload = form.cleaned_data['file_import']

        results = {
            'steps': [],
            'credential_type': _('Unknown'),
            'issuer_name': None,
            'issuer_id': None,
            'is_valid': False,
            'payload': None
        }

        try:
            file_content = upload.read().decode('utf-8')
            cred_data = json.loads(file_content)
            results['steps'].append({"name": _("Format parsing"), "status": "Success", "detail": _("Valid JSON document loaded.")})
        except Exception as e:
            results['steps'].append({"name": _("Format parsing"), "status": "Failed", "detail": _("Invalid JSON file.")})
            return self.render_to_response(self.get_context_data(form=form, results=results))

        if "verifiableCredential" in cred_data:
            cred_data = cred_data["verifiableCredential"]

        raw_types = cred_data.get("type", [])
        if isinstance(raw_types, str): raw_types = [raw_types]

        if "EnvelopedVerifiableCredential" in raw_types or str(cred_data.get("id", "")).startswith("data:application/vc+jwt"):
            self._verify_enveloped(cred_data, results)

        elif "proof" in cred_data:
            results['credential_type'] = f"JSON-LD Data Integrity ({', '.join(raw_types)})"
            self._extract_issuer(cred_data.get("issuer"), results)
            self._verify_standard(cred_data, file_content, results)

        else:
            results['steps'].append({"name": _("Type detection"), "status": "Failed", "detail": _("Missing proof block or enveloped JWT URI.")})

        return self.render_to_response(self.get_context_data(form=form, results=results))

    def _extract_issuer(self, issuer_data, results):
        if isinstance(issuer_data, dict):
            results['issuer_name'] = issuer_data.get("name")
            results['issuer_id'] = issuer_data.get("id")
        else:
            results['issuer_name'] = None
            results['issuer_id'] = issuer_data

    def _verify_standard(self, cred_data, raw_str, results):
        try:
            sig_valid, sig_msg = verify_signature(raw_str, verify=True)
            results['steps'].append({
                "name": _("Cryptographic Integrity"),
                "status": "Success" if sig_valid else "Failed",
                "detail": _("Signature is mathematically valid.") if sig_valid else _("Signature verification failed: {}").format(sig_msg)
            })

            if sig_valid:
                self._run_schema_validation(cred_data, results)

        except Exception as e:
             results['steps'].append({"name": _("Verification Process"), "status": "Failed", "detail": str(e)})

    def _run_schema_validation(self, vc_dict, results):
        vc_dict = self._inject_untp_0_0_6_missing_schema(vc_dict)

        vc_str = json.dumps(vc_dict)
        schema_valid, schema_msg = verify_schema(vc_str, verify=True)

        results['steps'].append({
            "name": _("Schema Verification"),
            "status": "Success" if schema_valid else "Failed",
            "detail": _("The payload adheres strictly to the schema.") if schema_valid else _("Schema validation failed: {}").format(schema_msg)
        })

        results['is_valid'] = schema_valid
        results['payload'] = vc_dict.get("credentialSubject")

        if schema_valid:
            render_methods = vc_dict.get("renderMethod", [])
            if render_methods and isinstance(render_methods, list) and len(render_methods) > 0:
                results['html_template'] = render_methods[0].get("template")

        return schema_valid


    def _verify_enveloped(self, cred_data, results):
        """ experimental: UNTP JWT credentials """
        data_uri = cred_data.get("id", "")
        if "data:application/vc+jwt," not in data_uri:
            results['steps'].append({"name": _("JWT Extraction"), "status": "Failed", "detail": _("Invalid Data URI format.")})
            return

        jwt_string = data_uri.split("data:application/vc+jwt,")[1]
        results['steps'].append({"name": _("JWT Extraction"), "status": "Success", "detail": _("JWT successfully extracted from envelope.")})

        try:
            unverified_header = jwt.get_unverified_header(jwt_string)
            kid = unverified_header.get("kid")
            issuer_did = kid.split("#")[0]

            did_doc = resolve_did(issuer_did)

            if not did_doc:
                raise ValueError(_("Failed to resolve DID Document for issuer: {}").format(issuer_did))

            public_jwk = next((m.get("publicKeyJwk") for m in did_doc.get("verificationMethod", []) if m["id"] == kid), None)

            if not public_jwk:
                raise ValueError(_("Verification key not found in the issuer's DID document."))

            eddsa_alg = get_default_algorithms()["EdDSA"]
            public_key_obj = eddsa_alg.from_jwk(json.dumps(public_jwk))

            decoded_payload = jwt.decode(jwt_string, public_key_obj, algorithms=["EdDSA"])
            trusted_vc = decoded_payload.get("vc", decoded_payload)

            if not trusted_vc:
                raise ValueError(_("The token is mathematically valid, but the payload is empty."))

            results['steps'].append({
                "name": _("Cryptographic Integrity"),
                "status": "Success",
                "detail": _("Ed25519 signature mathematically validated against issuer DID.")
            })

            vc_types = trusted_vc.get("type", [])
            if isinstance(vc_types, str): vc_types = [vc_types]
            results['credential_type'] = f"W3C Enveloped JWT ({', '.join(vc_types)})"

            self._extract_issuer(trusted_vc.get("issuer"), results)

            self._run_schema_validation(trusted_vc, results)

        except jwt.ExpiredSignatureError:
            results['steps'].append({"name": _("Cryptographic Integrity"), "status": "Failed", "detail": _("The credential has expired.")})
        except jwt.InvalidSignatureError:
            results['steps'].append({"name": _("Cryptographic Integrity"), "status": "Failed", "detail": _("Signature verification failed. The data was tampered with.")})
        except Exception as e:
            results['steps'].append({"name": _("Verification Process"), "status": "Failed", "detail": str(e)})


    def _inject_untp_0_0_6_missing_schema(self, vc_dict):
        if "credentialSchema" in vc_dict:
            return vc_dict

        vc_types = vc_dict.get("type", [])
        if isinstance(vc_types, str):
            vc_types = [vc_types]

        schema_url = None
        if "DigitalProductPassport" in vc_types:
            schema_url = "https://test.uncefact.org/vocabulary/untp/dpp/untp-dpp-schema-0.6.0.json"
        elif "DigitalFacilityRecord" in vc_types:
            schema_url = "https://test.uncefact.org/vocabulary/untp/dfr/untp-dfr-schema-0.6.0.json"
        elif "DigitalTraceabilityEvent" in vc_types:
            schema_url = "https://test.uncefact.org/vocabulary/untp/dte/untp-dte-schema-0.6.0.json"

        if schema_url:
            vc_dict["credentialSchema"] = {
                "type": "FullJsonSchemaValidator2021",
                "id": schema_url
            }

        return vc_dict
