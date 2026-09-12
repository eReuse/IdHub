import base64
from datetime import datetime, timezone
import ipaddress
import json
import logging
import socket
from typing import Any, List, Tuple
from urllib.parse import unquote, urlparse

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
import jwt
from pyvckit.verify import resolve_did, verify_schema, verify_signature

from idhub.models import DID, Schemas, VerificableCredential

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

            # satisfy strict JSON-LD validators
            absolute_iri = "https://w3id.org/security#FullJsonSchemaValidator2021"
            if hasattr(schema, 'schema_type') and schema.schema_type == 'FullJsonSchemaValidator2021':
                schema.schema_type = absolute_iri
            elif hasattr(schema, 'type') and schema.type == 'FullJsonSchemaValidator2021':
                schema.type = absolute_iri

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
    def sync_endpoint_to_document(obj_did: DID):
        if not obj_did.didweb_document:
            doc = {"@context": ["https://www.w3.org/ns/did/v1"], "id": obj_did.did}
        else:
            try:
                doc = json.loads(obj_did.didweb_document)
            except json.JSONDecodeError:
                doc = {"@context": ["https://www.w3.org/ns/did/v1"], "id": obj_did.did}

        if "service" in doc:
            doc["service"] = [s for s in doc["service"] if s.get("type") != "ProductPassport"]
        else:
            doc["service"] = []

        if obj_did.service_endpoint:
            doc["service"].append({
                "id": f"{obj_did.did}#product",
                "type": "ProductPassport",
                "serviceEndpoint": obj_did.service_endpoint
            })

        if not doc["service"]:
            del doc["service"]

        obj_did.didweb_document = json.dumps(doc)
        return obj_did

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
                    DIDService.sync_endpoint_to_document(existing_did)
                    existing_did.save(update_fields=['service_endpoint', 'didweb_document'])
                return existing_did, False

        # create new DID
        obj_did = DID(
            user=user,
            label=label,
            type=did_type,
            is_product=True,
            service_endpoint=service_endpoint or ""
        )

        obj_did.set_did()
        if expected_did:
            obj_did.did = expected_did

        obj_did.get_did_document()

        DIDService.sync_endpoint_to_document(obj_did)

        obj_did.save()

        return obj_did, True

class VerificationService:

    # TODO: move this logic to pyvckit?
    @classmethod
    def validate_safe_host(cls, host: str, port: int = 443):
        """
        Verifies that a hostname does not resolve to private, loopback,
        link-local, multicast, or non-global IP addresses (anti-SSRF).
        """
        if not host:
            raise ValueError(_("Host name cannot be empty."))

        clean_host = host.strip("[]")

        try:
            addr_info = socket.getaddrinfo(clean_host, port, type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise ValueError(_(f"Unable to resolve host '{host}'."))

        for item in addr_info:
            ip_str = item[4][0]
            ip_obj = ipaddress.ip_address(ip_str)

            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_reserved
                or ip_obj.is_link_local
                or ip_obj.is_multicast
                or not ip_obj.is_global
            ):
                raise ValueError(
                    _("Access to private, loopback, or reserved network addresses is prohibited.")
                )

    @classmethod
    def validate_safe_did(cls, did: str):
        """
        Validates did:web hosts against internal network endpoints.
        """
        if not isinstance(did, str) or not did.startswith("did:web:"):
            return

        parts = did.split(":")
        if len(parts) < 3:
            raise ValueError(_("Malformed did:web string."))

        raw_domain = unquote(parts[2])
        parsed = urlsplit(f"//{raw_domain}")
        host = parsed.hostname
        port = parsed.port or 443

        cls.validate_safe_host(host, port)

    @classmethod
    def validate_safe_contexts(cls, context_field: Any):
        """
        Validates remote JSON-LD context URLs against SSRF before pyld resolves them.
        """
        if isinstance(context_field, str):
            urls = [context_field]
        elif isinstance(context_field, list):
            urls = [item for item in context_field if isinstance(item, str)]
        elif isinstance(context_field, dict):
            urls = [v for v in context_field.values() if isinstance(v, str)]
        else:
            urls = []

        for url in urls:
            if url.startswith("http://") or url.startswith("https://"):
                parsed = urlsplit(url)
                port = parsed.port or (80 if parsed.scheme == "http" else 443)
                cls.validate_safe_host(parsed.hostname, port)

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

    @staticmethod
    def _format_exception(e: Exception) -> str:
        """Extracts a clean, human-readable message from complex nested exceptions (like JSON-LD errors)."""
        if type(e).__name__ == "JsonLdError" or hasattr(e, 'code'):
            code = getattr(e, 'code', '')
            details = getattr(e, 'details', {})

            if code == 'loading remote context failed':
                url = details.get('url', 'Unknown URL')
                return str(_("Failed to fetch remote JSON-LD context. The server might be down or inaccessible: {}")).format(url)

            cause = getattr(e, 'cause', None)
            if cause:
                return f"JSON-LD Parsing Error: {type(cause).__name__}"

        msg = str(e)
        if msg.startswith("('") and msg.endswith("',)"):
            msg = msg[2:-3]

        return msg.split('\n')[0].strip()

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
        raw = raw.strip()

        if raw.startswith("eyJ"):
            cls.add_step(results, _("Format parsing"), True, _("Raw JWT string loaded."))
            return {"type": "EnvelopedVerifiableCredential", "id": f"data:application/vc+jwt,{raw}"}

        try:
            doc = json.loads(raw)
            cls.add_step(results, _("Format parsing"), True, _("Valid JSON document loaded."))

            if "verifiableCredential" in doc:
                doc["verifiableCredential"]["_was_unwrapped"] = True
                return doc["verifiableCredential"]
            return doc
        except Exception:
            cls.add_step(results, _("Format parsing"), False, _("Invalid JSON or JWT file."))
            return None

    @classmethod
    def _unwrap_and_verify(cls, doc: dict, raw_str: str, results: dict):
        raw_types = doc.get("type", [])
        if isinstance(raw_types, str):
            raw_types = [raw_types]

        # either a JWT enveloped credential
        if "EnvelopedVerifiableCredential" in raw_types or str(doc.get("id", "")).startswith("data:application/vc+jwt"):
            return cls._verify_jwt_branch(doc, results)

        # or normal open credential (JSON-LD)
        elif "proof" in doc:
            results['credential_type'] = f"JSON-LD Data Integrity ({', '.join(raw_types)})"
            try:
                if "@context" in doc:
                    cls.validate_safe_contexts(doc["@context"])

                proof = doc.get("proof", {})
                verification_method = proof.get("verificationMethod", "") if isinstance(proof, dict) else ""
                issuer_id = doc.get("issuer")
                if isinstance(issuer_id, dict):
                    issuer_id = issuer_id.get("id", "")

                target_did = verification_method.split("#")[0] if verification_method else str(issuer_id)
                cls.validate_safe_did(target_did)

                if doc.pop("_was_unwrapped", False):
                    string_to_verify = json.dumps(doc)
                else:
                    string_to_verify = raw_str

                sig_valid, sig_msg = verify_signature(string_to_verify, verify=True)
                if sig_valid:
                    cls.add_step(results, _("Cryptographic Integrity"), True, _("Signature is mathematically valid."))
                    return doc
                else:
                    cls.add_step(results, _("Cryptographic Integrity"), False, _(f"Signature verification failed: {sig_msg}"))
            except Exception as e:
                clean_msg = cls._format_exception(e)
                cls.add_step(results, _("Cryptographic Integrity"), False, clean_msg)
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
            if not kid:
                raise ValueError(_("Missing 'kid' parameter in JWT header."))

            issuer_did = kid.split("#")[0]

            cls.validate_safe_did(issuer_did)

            did_doc = resolve_did(issuer_did)
            if not did_doc:
                raise ValueError(_("Failed to resolve DID Document for issuer: {}").format(issuer_did))

            public_key_obj = cls._get_jwt_verify_key(kid, did_doc)
            decoded_payload = jwt.decode(jwt_string, public_key_obj, algorithms=["EdDSA"], options={"verify_aud": False})
            trusted_vc = decoded_payload.get("vc", decoded_payload)

            if not trusted_vc:
                raise ValueError(_("The token is mathematically valid, but the payload is empty."))

            if "@context" in trusted_vc:
                cls.validate_safe_contexts(trusted_vc["@context"])

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
            if isinstance(vc_types, str):
                vc_types = [vc_types]
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
        # TODO: check for better way to do this
        if "DigitalProductPassport" in vc_types:
            schema_url = "https://untp.unece.org/artefacts/schema/v0.7.0/dpp/DigitalProductPassport.json"
        elif "DigitalFacilityRecord" in vc_types:
            schema_url = "https://untp.unece.org/artefacts/schema/v0.7.0/dfr/DigitalFacilityRecord.json"
        elif "DigitalTraceabilityEvent" in vc_types:
            schema_url = "https://untp.unece.org/artefacts/schema/v0.7.0/dte/DigitalTraceabilityEvent.json"

        if schema_url:
            vc_dict["credentialSchema"] = {
                "type": "https://w3id.org/security#FullJsonSchemaValidator2021",
                "id": schema_url
            }
        return vc_dict
