#!/usr/bin/env python3

import json
import logging
import hashlib
from typing import Any, List, Tuple

from django.conf import settings
from django.db import transaction

from pyvckit.sign import sign
from idhub.models import DID
from pyvckit.verify import verify_schema, verify_signature

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

                rendered_json_str = cred.render(domain)

                # verify schema
                verify_env = not settings.DEBUG
                valid, error_details = verify_schema(rendered_json_str, verify=verify_env)

                if not valid:
                    logger.warning("Schema validation failed prior to signing.")
                    return 400, {'error': 'Schema validation failed prior to signing.', 'details': error_details}

                # prepare cryptography signing
                cred.set_issue_date()
                cred.hash = hashlib.sha3_256(rendered_json_str.encode()).hexdigest()
                key = issuer_did_obj.get_key_material()

                try:
                    vc = sign(rendered_json_str, key, issuer_did_obj.did, verify=verify_env)
                    vc_str = json.dumps(vc)
                except Exception as sign_exc:
                    logger.error(f"Cryptographic signing failed for DID {issuer_did_obj.did}: {sign_exc}", exc_info=True)
                    return 500, {'error': 'Internal server error during cryptographic signing.'}

                # should these post validation be avoided?
                sig_valid, sig_err = verify_signature(vc_str, verify=verify_env)
                if not sig_valid:
                    logger.error(f"Post-sign signature validation failed: {sig_err}")
                    raise ValueError("The generated cryptographic signature is invalid.")


                cred.issue(did=subject_did, domain=domain, save=True)

                return 201, {"credential": json.loads(cred.get_data())}

        except ValueError as e:
            return 400, {'error': str(e)}
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

        if suffix_did_id and did_type == DID.Types.WEB.value:
            obj_did.did = expected_did
        else:
            obj_did.set_did()

        obj_did.save()

        return obj_did, True
