import asyncio
import datetime
import didkit
import json
import jinja2


def generate_did_controller_key():
    return didkit.generate_ed25519_key()


def keydid_from_controller_key(key):
    return didkit.key_to_did("key", key)


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


def verify_credential(vc, proof_options):
    """
    Returns a (bool, str) tuple indicating whether the credential is valid.
    If the boolean is true, the credential is valid and the second argument can be ignored.
    If it is false, the VC is invalid and the second argument contains a JSON object with further information.
    """
    async def inner():
        return didkit.verify_credential(vc, proof_options)

    return asyncio.run(inner())
