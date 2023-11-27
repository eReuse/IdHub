import json

from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect
from .models import VPVerifyRequest
from django.shortcuts import get_object_or_404
from more_itertools import flatten, unique_everseen


def verify(request):
    assert request.method == "POST"
    # TODO: use request.POST["presentation_submission"]
    vp = json.loads(request.POST["vp_token"])
    nonce = vp["nonce"]
    # "vr" = verification_request
    vr = get_object_or_404(VPVerifyRequest, nonce=nonce)  # TODO: return meaningful error, not 404
    # Get a list of all included verifiable credential types
    included_credential_types = unique_everseen(flatten([
        vc["type"] for vc in vp["verifiableCredential"]
    ]))
    # Check that it matches what we requested
    for requested_vc_type in json.loads(vr.expected_credentials):
        if requested_vc_type not in included_credential_types:
            raise Exception("You're missing some credentials we requested!")  # TODO: return meaningful error
    # Perform whatever action we have to do
    action = json.loads(vr.action)
    if action["action"] == "send_mail":
        subject = action["params"]["subject"]
        to_email = action["params"]["to"]
        from_email = "noreply@verifier-portal"
        body = request.POST["vp-token"]
        send_mail(
            subject,
            body,
            from_email,
            [to_email]
        )
    elif action["action"] == "something-else":
        pass
    else:
        raise Exception("Unknown action!")
    # OK! Your verifiable presentation was successfully presented.
    return HttpResponseRedirect(vr.response_or_redirect)

