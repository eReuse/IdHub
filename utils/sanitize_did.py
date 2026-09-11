import re

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def sanitize_url(url):
    patron = re.compile(
        r'^https://'
        #r'(localhost(?::\d+)?|[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)'
        r'([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)'
        r'(?:/(?!\.+(?:/|$))[a-zA-Z0-9_.-]+)*'
        r'$'
    )
    return patron.fullmatch(url) is not None


def sanitize_path(path):
    patron = re.compile(
        r'^'
        r'(?:/(?!\.+(?:/|$))[a-zA-Z0-9_.-]+)*'
        r'$'
    )
    return patron.fullmatch(path) is not None

def sanitize_didweb(did):
    if did[:8] != "did:web:" or "/" in did:
        raise ValidationError(_("This is not a correct DID web"))

    didp = did.split(":")

    if len(didp) < 3:
        raise ValidationError(_("This is not a correct DID web"))

    did_domain = didp[:3]
    did_path = didp[3:]

    didp = [x.lower() for x in did_domain] + did_path
    did = ":".join(didp)
    domain = didp[2]

    if not did_path:
        # base Level did
        url = f"https://{domain}/.well-known/did.json"
        path_to_validate = "/.well-known/did.json"
    else:
        # path level did
        url_path = "/".join(did_path)
        url = f"https://{domain}/{url_path}/did.json"
        path_to_validate = f"/{url_path}/did.json"

    if domain == settings.DOMAIN and len(didp) > 5:
        raise ValidationError(_("Only a double  path level is permitted for this domain."))

    url_field = forms.URLField()
    url_field.clean(url)
    if not sanitize_url(url) or not sanitize_path(path_to_validate):
        raise ValidationError(_("Is not a valid url"))

    try:
        url_field = forms.URLField()
        url_field.clean(url)
    except ValidationError:
        raise ValidationError(_("Is not a valid url"))

    return did
