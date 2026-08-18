import json
import base64
import jwt
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Any, List, Tuple

from django.utils.translation import gettext_lazy as _
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pyvckit.verify import verify_schema, verify_signature, resolve_did
from django.conf import settings
from django.db import transaction
from idhub.models import DID

from idhub.models import Schemas, VerificableCredential

logger = logging.getLogger(__name__)

class CredentialIssuanceService:
    @staticmethod
    def issue_untp_credential(
        user,
        schema_name: str,
        subject_data: Any,
        credential_type: List[str],
        subject_did,
        issuer_did_obj
    ) -> Tuple[int, dict]:
        """
        Handles the business logic for issuing a UNTP credential.
        """
        try:
            schema = Schemas.objects.get(file_schema=schema_name)
        except Schemas.DoesNotExist:
            logger.warning(f"User {user.id} requested non-existent schema: {schema_name}")
            return 422, {'error': f"Schema '{schema_name}' does not exist."}

        try:
            with transaction.atomic():
                domain = f"https://{settings.DOMAIN}/"

                cred = VerificableCredential(
                    verified=True,
                    user=user,
                    json_data=subject_data,
                    issuer_did=issuer_did_obj,
                    schema=schema,
                    type=credential_type,
                    subject_did=subject_did if subject_did else None
                )

                # pre verify schema  before doing intensive signing
                rendered_json_str = cred.render(domain)
                verify_env = not settings.DEBUG

                valid, error_details = verify_schema(rendered_json_str, verify=verify_env)
                if not valid:
                    logger.warning("Schema validation failed prior to signing.")
                    return 400, {'error': 'Schema validation failed prior to signing.', 'details': error_details}

                # issue() function will sign and validate the credential
                success, result = cred.issue(did=subject_did, domain=domain, save=True)
                if not success:
                    return 400, {'error': 'Issuance failed', 'details': result}

                return 201, {"credential": result}

        except Exception as e:
            logger.error(f"Issuance flow failed unexpectedly: {e}", exc_info=True)
            return 500, {'error': 'Internal server error during credential issuance.'}


class DIDService:
    @staticmethod
    def get_or_create_product_did(
        user,
        did_type: int,
        label: str,
        service_endpoint: str = "",
        suffix_did_id: str = None
    ):
        expected_did = None
        # check for existing did:web based on suffix
        if did_type == DID.Types.WEB.value and suffix_did_id:
            expected_did = f"did:web:{settings.DOMAIN}:{suffix_did_id}"
            existing_did = DID.objects.filter(did=expected_did, is_product=True).first()

            if existing_did:
                if service_endpoint and existing_did.service_endpoint != service_endpoint:
                    existing_did.service_endpoint = service_endpoint
                    existing_did.save(update_fields=['service_endpoint'])
                return existing_did, False  # false is that = not created, fetched existing

        # create new DID
        obj_did = DID(
            user=user,
            label=label,
            type=did_type,
            is_product=True,
            service_endpoint=service_endpoint or ""
        )

        if expected_did:
            obj_did.did = expected_did
        else:
            obj_did.set_did()

        obj_did.save()

        return obj_did, True


class VerificationService:

    @staticmethod
    def empty_results():
        return {
            'steps': [],
            'credential_type': _('Unknown'),
            'issuer_name': None,
            'issuer_id': None,
            'issuer_url': None,
            'is_valid': False,
            'payload': None,
            'html_template': None
        }

    @staticmethod
    def add_step(results, name, status, detail):
        results['steps'].append({
            "name": name,
            "status": "Success" if status else "Failed",
            "detail": detail
        })

    @classmethod
    def verify_document(cls, raw_str: str) -> dict:
        results = cls.empty_results()

        doc = cls._parse_json(raw_str, results)
        if not doc:
            return results

        trusted_vc = cls._unwrap_and_verify(doc, raw_str, results)

        if not trusted_vc:
            return results

        cls._check_schema(trusted_vc, results)
        cls._extract_issuer(trusted_vc, results)
        cls._extract_render_method(trusted_vc, results)

        return results

    @classmethod
    def _parse_json(cls, raw: str, results: dict):
        try:
            doc = json.loads(raw)
            cls.add_step(results, _("Format parsing"), True, _("Valid JSON document loaded."))

            if "verifiableCredential" in doc:
                return doc["verifiableCredential"]
            return doc
        except Exception:
            cls.add_step(results, _("Format parsing"), False, _("Invalid JSON file."))
            return None

    @classmethod
    def _unwrap_and_verify(cls, doc: dict, raw_str: str, results: dict):
        raw_types = doc.get("type", [])
        if isinstance(raw_types, str):
            raw_types = [raw_types]

        # either a JWT enveloped credential
        if "EnvelopedVerifiableCredential" in raw_types or str(doc.get("id", "")).startswith("data:application/vc+jwt"):
            return cls._verify_jwt_branch(doc, results)

        # or nomal open credential
        elif "proof" in doc:
            results['credential_type'] = f"JSON-LD Data Integrity ({', '.join(raw_types)})"
            try:
                sig_valid, sig_msg = verify_signature(raw_str, verify=True)
                if sig_valid:
                    cls.add_step(results, _("Cryptographic Integrity"), True, _("Signature is mathematically valid."))
                    return doc
                else:
                    cls.add_step(results, _("Cryptographic Integrity"), False, _(f"Signature verification failed: {sig_msg}"))
            except Exception as e:
                cls.add_step(results, _("Cryptographic Integrity"), False, str(e))
            return None

        else:
            cls.add_step(results, _("Type detection"), False, _("Missing proof block or enveloped JWT URI."))
            return None

    @classmethod
    def _verify_jwt_branch(cls, doc: dict, results: dict):
        data_uri = doc.get("id", "")
        if "data:application/vc+jwt," not in data_uri:
            cls.add_step(results, _("JWT Extraction"), False, _("Invalid Data URI format."))
            return None

        jwt_string = data_uri.split("data:application/vc+jwt,")[1]
        cls.add_step(results, _("JWT Extraction"), True, _("JWT successfully extracted from envelope."))

        try:
            unverified_header = jwt.get_unverified_header(jwt_string)
            kid = unverified_header.get("kid")
            issuer_did = kid.split("#")[0]

            did_doc = resolve_did(issuer_did)
            if not did_doc:
                raise ValueError(_("Failed to resolve DID Document for issuer: {}").format(issuer_did))

            public_key_obj = cls._get_jwt_verify_key(kid, did_doc)
            decoded_payload = jwt.decode(jwt_string, public_key_obj, algorithms=["EdDSA"], options={"verify_aud": False})
            trusted_vc = decoded_payload.get("vc", decoded_payload)

            if not trusted_vc:
                raise ValueError(_("The token is mathematically valid, but the payload is empty."))

            now = datetime.now(timezone.utc)
            valid_from_str = trusted_vc.get("validFrom") or trusted_vc.get("issuanceDate")
            if valid_from_str:
                valid_from = datetime.strptime(valid_from_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if now < valid_from:
                    raise ValueError(_("The credential is not yet valid."))

            valid_until_str = trusted_vc.get("validUntil") or trusted_vc.get("expirationDate")
            if valid_until_str:
                valid_until = datetime.strptime(valid_until_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if now > valid_until:
                    raise ValueError(_("The credential has expired."))

            cls.add_step(results, _("Cryptographic Integrity"), True, _("Ed25519 signature validated against issuer DID and dates are valid."))

            vc_types = trusted_vc.get("type", [])
            if isinstance(vc_types, str): vc_types = [vc_types]
            results['credential_type'] = f"W3C Enveloped JWT ({', '.join(vc_types)})"

            return trusted_vc

        except jwt.InvalidSignatureError:
            cls.add_step(results, _("Cryptographic Integrity"), False, _("Signature verification failed. The data was tampered with."))
        except Exception as e:
            cls.add_step(results, _("Verification Process"), False, str(e))

        return None

    @classmethod
    def _check_schema(cls, trusted_vc: dict, results: dict):
        trusted_vc = cls._inject_untp_0_0_7_missing_schema(trusted_vc)
        vc_str = json.dumps(trusted_vc)

        schema_valid, schema_msg = verify_schema(vc_str, verify=True)
        results['is_valid'] = schema_valid
        results['payload'] = trusted_vc.get("credentialSubject")

        if schema_valid:
            cls.add_step(results, _("Schema Verification"), True, _("The payload adheres strictly to the schema."))
        else:
            cls.add_step(results, _("Schema Verification"), False, _(f"Schema validation failed: {schema_msg}"))

    @classmethod
    def _extract_issuer(cls, trusted_vc: dict, results: dict):
        issuer_data = trusted_vc.get("issuer", {})

        if isinstance(issuer_data, dict):
            results['issuer_name'] = issuer_data.get("name")
            issuer_id = issuer_data.get("id")
        else:
            results['issuer_name'] = None
            issuer_id = issuer_data

        results['issuer_id'] = issuer_id

        parsed_url = urlparse(str(issuer_id) if issuer_id else "")
        if parsed_url.scheme in ("http", "https"):
            results['issuer_url'] = issuer_id
        else:
            results['issuer_url'] = None

    @classmethod
    def _extract_render_method(cls, trusted_vc: dict, results: dict):
        if results['is_valid']:
            render_methods = trusted_vc.get("renderMethod", [])
            if render_methods and isinstance(render_methods, list) and len(render_methods) > 0:
                results['html_template'] = render_methods[0].get("template")

    @staticmethod
    def _get_jwt_verify_key(kid: str, did_document: dict):
        if not did_document or "verificationMethod" not in did_document:
            raise ValueError(_("Invalid or empty DID Document provided."))

        target_method = None
        for method in did_document["verificationMethod"]:
            method_id = method.get("id", "")
            if method_id == kid or method_id.endswith(f"#{kid.split('#')[-1]}"):
                target_method = method
                break

        if not target_method and len(did_document["verificationMethod"]) == 1:
            target_method = did_document["verificationMethod"][0]

        if not target_method:
            raise ValueError(_("Verification key matching '{}' not found in the DID document.").format(kid))

        if "publicKeyJwk" in target_method:
            x_b64 = target_method["publicKeyJwk"].get("x")
            if not x_b64:
                raise ValueError(_("publicKeyJwk is missing the 'x' coordinate."))
            x_b64 += "=" * ((4 - len(x_b64) % 4) % 4)
            raw_key_bytes = base64.urlsafe_b64decode(x_b64)

        elif "publicKeyMultibase" in target_method:
            raise ValueError(_("This verifier requires 'publicKeyJwk'. 'publicKeyMultibase' is not supported by this platform."))
        else:
            raise ValueError(_("Verification method contains unsupported key format."))

        try:
            return Ed25519PublicKey.from_public_bytes(raw_key_bytes)
        except Exception as e:
            raise ValueError(_("Failed to parse Ed25519 public key bytes: {}").format(str(e)))

    @staticmethod
    def _inject_untp_0_0_7_missing_schema(vc_dict: dict):
        if "credentialSchema" in vc_dict:
            return vc_dict

        vc_types = vc_dict.get("type", [])
        if isinstance(vc_types, str):
            vc_types = [vc_types]

        schema_url = None
        #TODO: check for better way to do this
        if "DigitalProductPassport" in vc_types:
            schema_url = "https://untp.unece.org/artefacts/schema/v0.7.0/dpp/DigitalProductPassport.json"
        elif "DigitalFacilityRecord" in vc_types:
            schema_url = "https://untp.unece.org/artefacts/schema/v0.7.0/dfr/DigitalFacilityRecord.json"
        elif "DigitalTraceabilityEvent" in vc_types:
            schema_url = "https://untp.unece.org/artefacts/schema/v0.7.0/dte/DigitalTraceabilityEvent.json"

        if schema_url:
            vc_dict["credentialSchema"] = {
                "type": "FullJsonSchemaValidator2021",
                "id": schema_url
            }

        return vc_dict
