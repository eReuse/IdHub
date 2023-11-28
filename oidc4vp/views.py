import json

from django.views.generic.edit import View

from oidc4vp.models import Authorization, Organization
from django.http import HttpResponse


# from django.core.mail import send_mail
# from django.http import HttpResponse, HttpResponseRedirect

# from utils.idhub_ssikit import verify_presentation
# from oidc4vp.models import VPVerifyRequest
from django.shortcuts import get_object_or_404
# from more_itertools import flatten, unique_everseen


class VerifyView(View):
    def get(self, request, *args, **kwargs):
        org_url = request.GET.get('demand_uri')
        org = get_object_or_404(Organization, response_uri=org_url)
        authorization = Authorization(
            organization=org,
            presentation_definition="MemberCredential"
        )
        import pdb; pdb.set_trace()
        res = json.dumps({"redirect_uri": authorization.authorize()})
        return HttpResponse(res)

    def post(self, request, *args, **kwargs):
        import pdb; pdb.set_trace()
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
