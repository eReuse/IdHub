"""Patches that keep the test suite offline and cheap.

pyvckit reaches the network from three different places: the JSON-LD
``@context`` loader, ``did:web`` resolution and ``credentialSchema``
validation. Patching ``requests.Session.request`` covers all three at once,
and turns an unforeseen URL into a loud failure instead of a silent
round trip that makes the suite take minutes.

The other cost is the argon2i key derivation behind every encrypted field,
hence ``FastKdfMixin``.
"""
import json
import os

from unittest.mock import patch
from urllib.parse import urlsplit

import requests

from nacl import pwhash

from django.conf import settings
from django.test import Client


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures', 'http')


class UnexpectedRequest(AssertionError):
    pass


def _json_response(url, payload):
    response = requests.Response()
    response.status_code = 200
    response.url = url
    response.headers['Content-Type'] = 'application/ld+json'
    response._content = json.dumps(payload).encode()
    return response


def _local_file(*parts):
    path = os.path.normpath(os.path.join(*parts))
    return path if os.path.isfile(path) else None


def _resolve(host, path):
    """Maps a remote URL onto a file shipped in the repository."""
    # The pilot contexts and schemas live in the working tree under their own
    # names, whatever host the credential points at.
    if path.startswith('/context/'):
        local = _local_file(settings.BASE_DIR, 'context', path[len('/context/'):])
        if local:
            return local
    if path.startswith('/vc_schemas/'):
        local = _local_file(settings.SCHEMAS_DIR, path[len('/vc_schemas/'):])
        if local:
            return local

    return _local_file(FIXTURES_DIR, host, path.lstrip('/'))


def offline_request(method, url, **kwargs):
    parts = urlsplit(url)
    path = parts.path

    if parts.hostname == settings.DOMAIN:
        # Credentials issued during the tests point their @context at this very
        # host, which is not resolvable by name.
        response = Client().get(path)
        if response.status_code != 200:
            raise UnexpectedRequest(
                "{} {} answered {}".format(method, url, response.status_code)
            )
        return _json_response(url, json.loads(response.content))

    local = _resolve(parts.hostname, path)
    if local is None:
        raise UnexpectedRequest(
            "{} {} is not available offline; add it under {}".format(
                method, url, os.path.join(FIXTURES_DIR, parts.hostname or '')
            )
        )

    with open(local) as f:
        return _json_response(url, json.load(f))


class OfflineHttpMixin:
    """Makes every outbound HTTP request resolve against local files."""

    def setUp(self):
        super().setUp()
        patcher = patch.object(
            requests.Session,
            'request',
            autospec=True,
            side_effect=lambda self, method, url, **kw: offline_request(
                method, url, **kw
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class FastKdfMixin:
    """Lowers the argon2i cost parameters, as PASSWORD_HASHERS does for login.

    Deriving a key takes 0.28 s with the interactive limits, and every
    encrypted field derives one. The limits are read inside
    ``derive_key_from_password`` on each call, so patching the module
    attributes is enough. Determinism and the failure modes are unaffected;
    only the work factor changes.
    """

    def setUp(self):
        super().setUp()
        for name, cheap in (
            ('OPSLIMIT_INTERACTIVE', pwhash.argon2i.OPSLIMIT_MIN),
            ('MEMLIMIT_INTERACTIVE', pwhash.argon2i.MEMLIMIT_MIN),
        ):
            patcher = patch.object(pwhash.argon2i, name, cheap)
            patcher.start()
            self.addCleanup(patcher.stop)
