#!/usr/bin/env python3

import json
import logging
import jsonschema
from ninja import NinjaAPI
from django.core.cache import cache
from django.conf import settings
from idhub.models import DID, Schemas, VerificableCredential
from .schemas import IssueCredentialPayload, ErrorResponse
from ninja.security import HttpBearer
from webhook.models import Token
from pyvckit.verify import verify_schema

api_v1 = NinjaAPI(version='1.0.0', title="IdHub v1 API")

logger = logging.getLogger(__name__)

class DatabaseTokenAuth(HttpBearer):
    def authenticate(self, request, token_string):
        try:
            token_obj = Token.objects.select_related('owner').get(
                token=token_string,
                active=True
            )
            return token_obj.owner

        except Token.DoesNotExist:
            logger.warning(f"Authentication failed: Token not found or inactive.")
            return None
        except (ValueError, TypeError):
            logger.warning(f"Authentication failed: Invalid token format.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during authentication: {e}", exc_info=True)
            return None


@api_v1.post("issue-credential/",
             response={201: dict,
                       400: ErrorResponse,
                       401: ErrorResponse,
                       404: ErrorResponse, 409: ErrorResponse, 422: ErrorResponse,
                       500: ErrorResponse
                       },
             summary="Create and Issue a Digital Product Passport",
             auth=DatabaseTokenAuth()
             )
def issue_credential(request, payload: IssueCredentialPayload):

    api_user = request.auth
    if not api_user:
        return 401, {'error': 'Authentication failed or user not active.'}

    if not cache.get("KEY_DIDS"):
        logger.error("Server configuration error: The 'KEY_DIDS' encryption key is not available in the cache.")
        return 500, {'error': "Server configuration error: The encryption key required for DID creation is not set up."}
    try:

        issuer_did = DID.objects.filter(user__isnull=True, is_product=False).first()
        if not issuer_did:
            raise DID.DoesNotExist("No organizational issuer DID found.")
        schema = Schemas.objects.get(file_schema=payload.schema_name)

    except Schemas.DoesNotExist:
        return 422, {'error': f"Schema with type or filename '{payload.schema_name}' not found."}
    except DID.DoesNotExist as e:
        return 500, {'error': f'Configuration error: {str(e)}'}

    cleaned_subject = payload.credentialSubject.copy()
    subject_id = cleaned_subject.get("id")
    if not subject_id:
        return 400, {'error': 'credentialSubject must contain an "id" field.'}

    obj_did = None
    # Check for existing credentials to prevent duplicates
    if VerificableCredential.objects.filter(schema=schema, issuer_did=issuer_did, status=VerificableCredential.Status.ISSUED,
                                            subject_id=subject_id).exists():

        return 409, {'error': 'A credential for this subject already exists.'}

    if payload.create_did:
        if not payload.service_endpoint:
            return 400, {'error': 'service_endpoint is required when create_did is true.'}

        label = cleaned_subject.get("id") or cleaned_subject.get("name") or "object-did"
        obj_did = DID(
            label=label,
            type=DID.Types.WEB,
            is_product=True,
            service_endpoint=payload.service_endpoint
        )
        obj_did.set_did()
        obj_did.save()

        cleaned_subject["id"] = obj_did.did
        subject_id = obj_did.did


    try:
        domain = f"https://{settings.DOMAIN}/"
        cred = VerificableCredential(
            verified=True,
            user=api_user,
            json_data=cleaned_subject,
            subject_id=subject_id,
            issuer_did=issuer_did,
            schema=schema,
        )
        cred.set_type()


        verify = not settings.DEBUG
        # Validate the final rendered JSON against the schema before signing
        rendered_json_str = cred.render(domain)
        valid, _ = verify_schema(rendered_json_str, verify=verify)
        if not valid:
            return 400, {'error': 'Schema validation failed.', 'details': e.message, 'path': list(e.path)}

        cred.issue(did=obj_did, domain=domain)
        cred.save()

    except jsonschema.exceptions.ValidationError as e:
        return 400, {'error': 'Schema validation failed.', 'details': e.message, 'path': list(e.path)}
    except Exception as e:
        logger.error(f'Error issuing credential: {e}', exc_info=True)
        return 500, {'error': f'Failed to create or issue credential: {str(e)}'}

    signed_credential_str = cred.get_data()
    signed_credential_json = json.loads(signed_credential_str)

    return 201, signed_credential_json
