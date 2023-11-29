import json
import base64

from django.conf import settings
from django.views.generic.edit import View, FormView
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy

from oidc4vp.models import Authorization, Organization
from idhub.mixins import UserView

from oidc4vp.forms import AuthorizeForm


# from django.core.mail import send_mail
# from django.http import HttpResponse, HttpResponseRedirect

# from utils.idhub_ssikit import verify_presentation
# from oidc4vp.models import VPVerifyRequest
# from more_itertools import flatten, unique_everseen


class AuthorizeView(UserView, FormView):
    title = _("My wallet")
    section = "MyWallet"
    template_name = "credentials_presentation.html"
    subtitle = _('Credential presentation')
    icon = 'bi bi-patch-check-fill'
    form_class = AuthorizeForm
    success_url = reverse_lazy('idhub:user_demand_authorization')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        vps = self.request.GET.get('presentation_definition')
        # import pdb; pdb.set_trace()
        kwargs['presentation_definition'] = json.loads(vps)
        return kwargs
    
    def form_valid(self, form):
        authorization = form.save()
        if authorization:
            return redirect(authorization)
        else:
            messages.error(self.request, _("Error sending credential!"))
        return super().form_valid(form)


class VerifyView(View):
    def get(self, request, *args, **kwargs):
        org = self.validate(request)
        presentation_definition = json.dumps(settings.SUPPORTED_CREDENTIALS)
        authorization = Authorization(
            organization=org,
            presentation_definition=presentation_definition
        )
        res = json.dumps({"redirect_uri": authorization.authorize()})
        return HttpResponse(res)

    def validate(self, request):
        auth_header = request.headers.get('Authorization', b'')
        auth_data = auth_header.split()

        if len(auth_data) == 2 and auth_data[0].lower() == 'basic':
            decoded_auth = base64.b64decode(auth_data[1]).decode('utf-8')
            client_id, client_secret = decoded_auth.split(':', 1)
            org_url = request.GET.get('demand_uri')
            org = get_object_or_404(
                Organization,
                response_uri=org_url,
                client_id=client_id,
                client_secret=client_secret
            )
            return org

        raise Http404("Organization not found!")

    def post(self, request, *args, **kwargs):
        org = self.validate(request)
        # import pdb; pdb.set_trace()
        # # TODO: incorporate request.POST["presentation_submission"] as schema definition
        # (presentation_valid, _) = verify_presentation(request.POST["vp_token"])
        # if not presentation_valid:
        #     raise Exception("Failed to verify signature on the given Verifiable Presentation.")
        # vp = json.loads(request.POST["vp_token"])
        # nonce = vp["nonce"]
        # # "vr" = verification_request
        # vr = get_object_or_404(VPVerifyRequest, nonce=nonce)  # TODO: return meaningful error, not 404
        # # Get a list of all included verifiable credential types
        # included_credential_types = unique_everseen(flatten([
        #     vc["type"] for vc in vp["verifiableCredential"]
        # ]))
        # # Check that it matches what we requested
        # for requested_vc_type in json.loads(vr.expected_credentials):
        #     if requested_vc_type not in included_credential_types:
        #         raise Exception("You're missing some credentials we requested!")  # TODO: return meaningful error
        # # Perform whatever action we have to do
        # action = json.loads(vr.action)
        # if action["action"] == "send_mail":
        #     subject = action["params"]["subject"]
        #     to_email = action["params"]["to"]
        #     from_email = "noreply@verifier-portal"
        #     body = request.POST["vp-token"]
        #     send_mail(
        #         subject,
        #         body,
        #         from_email,
        #         [to_email]
        #     )
        # elif action["action"] == "something-else":
        #     pass
        # else:
        #     raise Exception("Unknown action!")
        # # OK! Your verifiable presentation was successfully presented.
        # return HttpResponseRedirect(vr.response_or_redirect)
