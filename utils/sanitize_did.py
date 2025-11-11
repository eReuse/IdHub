import re

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


def sanitize_url(url):
    patron = re.compile(
        r'^https://'
        r'([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)'
        r'(?:/[a-zA-Z0-9-_]+)*'
        r'(?:/[a-zA-Z0-9-_]+)?'
        r'$'
    )
    return patron.fullmatch(url) is not None


def sanitize_path(path):
    patron = re.compile(
        r'(?:/[a-zA-Z0-9-_]+)*'
        r'(?:/[a-zA-Z0-9-_]+)?'
        r'$'
    )
    return patron.fullmatch(path) is not None


def sanitize_didweb(did):
    if did[:8] != "did:web:" or "/" in did:
        raise ValidationError(_("This is not a correct DID web"))

    didp = did.split(":")
    domain_path = didp[2:]
    did_domain = didp[:3]
    did_path = didp[3:]

    didp = [x.lower() for x in did_domain] + did_path
    did = ":".join(didp)
    domain = didp[2]

    # wellknown case
    #   expected 4 parts: did, web, domain, filename
    if domain == settings.DOMAIN and len(didp) != 4:
        raise ValidationError(_("You can't use path in the DID"))

    url = "https://" + "/".join(domain_path)
    path = "/" + "/".join(did_path)
    if not sanitize_url(url) or not sanitize_path(path):
        raise ValidationError(_("Is not a valid url"))

    url_field = forms.URLField()
    url_field.clean(url)

    return did
