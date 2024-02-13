import asyncio
import base64
import datetime
import zlib
from ast import literal_eval

import didkit
import json
import urllib
import jinja2
from django.template.backends.django import Template
from django.template.loader import get_template
from pyroaring import BitMap

from trustchain_idhub import settings


def generate_did_controller_key():
    return didkit.generate_ed25519_key()


def keydid_from_controller_key(key):
    return didkit.key_to_did("key", key)


def resolve_did(keydid):
    async def inner():
        return await didkit.resolve_did(keydid, "{}")

    return asyncio.run(inner())


def webdid_from_controller_key(key):
    """
    Se siguen los pasos para generar un webdid a partir de un keydid.
    Documentado en la docu de spruceid.
    """
    keydid = keydid_from_controller_key(key)  # "did:key:<...>"
    pubkeyid = keydid.rsplit(":")[-1]  # <...>
    document = json.loads(resolve_did(keydid))  # Documento DID en terminos "key"
    domain = urllib.parse.urlencode({"domain": settings.DOMAIN})[7:]
    webdid_url = f"did:web:{domain}:did-registry:{pubkeyid}"  # nueva URL: "did:web:idhub.pangea.org:<...>"
    webdid_url_owner = webdid_url + "#owner"
    # Reemplazamos los campos del documento DID necesarios:
    document["id"] = webdid_url
    document["verificationMethod"][0]["id"] = webdid_url_owner
    document["verificationMethod"][0]["controller"] = webdid_url
    document["authentication"][0] = webdid_url_owner
    document["assertionMethod"][0] = webdid_url_owner
    document_fixed_serialized = json.dumps(document)
    return webdid_url, document_fixed_serialized


def generate_generic_vc_id():
    # TODO agree on a system for Verifiable Credential IDs
    return "https://pangea.org/credentials/42"


def render_and_sign_credential(vc_template: jinja2.Template, jwk_issuer, vc_data: dict[str, str]):
    """
    Populates a VC template with data for issuance, and signs the result with the provided key.

    The `vc_data` parameter must at a minimum include:
        * issuer_did
        * subject_did
        * vc_id
    and must include whatever other fields are relevant for the vc_template to be instantiated.

    The following field(s) will be auto-generated if not passed in `vc_data`:
        * issuance_date (to `datetime.datetime.now()`)
    """
    async def inner():
        unsigned_vc = vc_template.render(vc_data)
        signed_vc = await didkit.issue_credential(
            unsigned_vc,
            '{"proofFormat": "ldp"}',
            jwk_issuer
        )
        return signed_vc

    if vc_data.get("issuance_date") is None:
        vc_data["issuance_date"] = datetime.datetime.now().replace(microsecond=0).isoformat()

    return asyncio.run(inner())

    
def sign_credential(unsigned_vc: str, jwk_issuer):
    """
    Signs the unsigned credential with the provided key.
    The credential template must be rendered with all user data.
    """
    async def inner():
        signed_vc = await didkit.issue_credential(
            unsigned_vc,
            '{"proofFormat": "ldp"}',
            jwk_issuer
        )
        return signed_vc

    return asyncio.run(inner())


def verify_credential(vc):
    """
    Returns a (bool, str) tuple indicating whether the credential is valid.
    If the boolean is true, the credential is valid and the second argument can be ignored.
    If it is false, the VC is invalid and the second argument contains a JSON object with further information.
    """
    async def inner():
        str_res = await didkit.verify_credential(vc, '{"proofFormat": "ldp"}')
        res = literal_eval(str_res)
        ok = res["warnings"] == [] and res["errors"] == []
        return ok, str_res

    valid, reason = asyncio.run(inner())
    if not valid:
        return valid, reason
    # Credential passes basic signature verification. Now check it against its schema.
    # TODO: check agasint schema
    pass
    # Credential verifies against its schema. Now check revocation status.
    vc = json.loads(vc)
    if "credentialStatus" in vc:
        revocation_index = int(vc["credentialStatus"]["revocationBitmapIndex"])  # NOTE: THIS FIELD SHOULD BE SERIALIZED AS AN INTEGER, BUT IOTA DOCUMENTAITON SERIALIZES IT AS A STRING. DEFENSIVE CAST ADDED JUST IN CASE.
        vc_issuer = vc["issuer"]["id"]  # This is a DID
        if vc_issuer[:7] == "did:web":  # Only DID:WEB can revoke
            issuer_did_document = json.loads(resolve_did(vc_issuer))  # TODO: implement a caching layer so we don't have to fetch the DID (and thus the revocation list) every time a VC is validated.
            issuer_revocation_list = issuer_did_document["service"][0]
            assert issuer_revocation_list["type"] == "RevocationBitmap2022"
            revocation_bitmap = BitMap.deserialize(
                zlib.decompress(
                    base64.b64decode(
                        issuer_revocation_list["serviceEndpoint"].rsplit(",")[1]
                    )
                )
            )
            if revocation_index in revocation_bitmap:
                return False, "Credential has been revoked by the issuer"
    # Fallthrough means all is good.
    return True, "Credential passes all checks"


def issue_verifiable_presentation(vp_template: Template, vc_list: list[str], jwk_holder: str, holder_did: str) -> str:
    async def inner():
        unsigned_vp = vp_template.render(data)
        signed_vp = await didkit.issue_presentation(
            unsigned_vp,
            '{"proofFormat": "ldp"}',
            jwk_holder
        )
        return signed_vp

    data = {
        "holder_did": holder_did,
        "verifiable_credential_list": "[" + ",".join(vc_list) + "]"
    }

    return asyncio.run(inner())


def create_verifiable_presentation(jwk_holder: str, unsigned_vp: str) -> str:
    async def inner():
        signed_vp = await didkit.issue_presentation(
            unsigned_vp,
            '{"proofFormat": "ldp"}',
            jwk_holder
        )
        return signed_vp

    return asyncio.run(inner())


def verify_presentation(vp):
    """
    Returns a (bool, str) tuple indicating whether the credential is valid.
    If the boolean is true, the credential is valid and the second argument can be ignored.
    If it is false, the VC is invalid and the second argument contains a JSON object with further information.
    """
    async def inner():
        proof_options = '{"proofFormat": "ldp"}'
        return await didkit.verify_presentation(vp, proof_options)

    return asyncio.run(inner())

