import json

from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect

from utils.idhub_ssikit import verify_presentation
from .models import VPVerifyRequest
from django.shortcuts import get_object_or_404
# from more_itertools import flatten, unique_everseen
from oidc4vp.models import Authorization


# class PeopleListView(People, TemplateView):
#     template_name = "idhub/admin/people.html"
#     subtitle = _('View users')
#     icon = 'bi bi-person'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context.update({
#             'users': User.objects.filter(),
#         })
#         return context


def DemandAuthorizationView(request):
    assert request.method == "GET"
    import pdb; pdb.set_trace()
    params = request.GET.params
    org = Organization.objects.filter(
        url=params.get('redirect_uri')
    )
    authorization = Authorization(
        organization=org,
        presentation_definition="MemberCredential"
    )
    # authorization.save()
    res = json.dumps({"uri": authorization.authorize()})
    return HttpResponse(res)


def verify(request):
    import pdb; pdb.set_trace()
#     assert request.method == "POST"
#     # TODO: incorporate request.POST["presentation_submission"] as schema definition
#     (presentation_valid, _) = verify_presentation(request.POST["vp_token"])
#     if not presentation_valid:
#         raise Exception("Failed to verify signature on the given Verifiable Presentation.")
#     vp = json.loads(request.POST["vp_token"])
#     nonce = vp["nonce"]
#     # "vr" = verification_request
#     vr = get_object_or_404(VPVerifyRequest, nonce=nonce)  # TODO: return meaningful error, not 404
#     # Get a list of all included verifiable credential types
#     included_credential_types = unique_everseen(flatten([
#         vc["type"] for vc in vp["verifiableCredential"]
#     ]))
#     # Check that it matches what we requested
#     for requested_vc_type in json.loads(vr.expected_credentials):
#         if requested_vc_type not in included_credential_types:
#             raise Exception("You're missing some credentials we requested!")  # TODO: return meaningful error
#     # Perform whatever action we have to do
#     action = json.loads(vr.action)
#     if action["action"] == "send_mail":
#         subject = action["params"]["subject"]
#         to_email = action["params"]["to"]
#         from_email = "noreply@verifier-portal"
#         body = request.POST["vp-token"]
#         send_mail(
#             subject,
#             body,
#             from_email,
#             [to_email]
#         )
#     elif action["action"] == "something-else":
#         pass
#     else:
#         raise Exception("Unknown action!")
#     # OK! Your verifiable presentation was successfully presented.
#     return HttpResponseRedirect(vr.response_or_redirect)

