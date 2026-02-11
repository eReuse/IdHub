#!/usr/bin/env python3

import json
import logging
import jsonschema
from ninja import NinjaAPI
from typing import List, Any, Optional

from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.db import transaction
from django.conf import settings
from idhub.models import DID, Schemas, VerificableCredential
from .schemas import IssueDPPayload, IssueTraceabilityPayload, IssueFacilityPayload, SignedCredentialResponse, ErrorResponse
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
            request.user = token_obj.owner
            return request.user

        except Token.DoesNotExist:
            logger.warning(f"Authentication failed: Token not found or inactive.")
            return None
        except (ValueError, TypeError):
            logger.warning(f"Authentication failed: Invalid token format.")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during authentication: {e}", exc_info=True)
            return None

def resolve_issuer(requested_did: str, user):
    if not requested_did:
        raise ValueError(f"Requested Issuer DID '{requested_did}' not found on this server.")
    issuer = DID.objects.filter(did=requested_did, is_product=False, user__isnull=True).first()
    if not issuer:
        raise PermissionDenied(f"You do not own the Issuer DID '{requested_did}' or it doesnt exists.")

    return issuer

def resolve_or_create_subject_did(suffix: Optional[str], service_endpoint: Optional[str], user, label: str = "product-did"):
    domain = settings.DOMAIN
    expected_did = f"did:web:{domain}:{suffix}"

    if suffix:
        existing_did = DID.objects.filter(did=expected_did).first()
        if existing_did:
            return existing_did, False

    if not service_endpoint:
        raise ValueError("A service endpoint is required to create a new DID.")

    obj_did = DID.objects.create(
            did=expected_did,
            label=label,
            type=DID.Types.WEB,
            is_product=True,
            user=None,
            service_endpoint=service_endpoint
    )
    obj_did.set_did()
    obj_did.save()

    return obj_did, True


@api_v1.post("issue-dpp/",
             response={201: SignedCredentialResponse,
                       400: ErrorResponse,
                       403: ErrorResponse,
                       409: ErrorResponse,
                       500: ErrorResponse},
             summary="Issue Digital Product Passport",
             auth=DatabaseTokenAuth())
def issue_dpp_credential(request, payload: IssueDPPayload):

    try:
        issuer_did = resolve_issuer(payload.issuer_did, request.user)
    except PermissionDenied as e:
        return 403, {'error': str(e)}
    except ValueError as e:
        return 400, {'error': str(e)}

    cleaned_subject = payload.credentialSubject.copy()
    subject_id = cleaned_subject.get("id")

    if payload.create_did:
        label = cleaned_subject.get("name") or "product-did"

        try:
            obj_did, created = resolve_or_create_subject_did(
                suffix=payload.subject_did_suffix,
                service_endpoint=payload.service_endpoint,
                user=None,
                label=label
            )
            cleaned_subject["id"] = obj_did.did
            subject_id = obj_did.did

        except PermissionDenied as e:
            return 403, {'error': str(e)}
        except ValueError as e:
            return 400, {'error': str(e)}
        except Exception as e:
            return 500, {'error': f'Unexpected error: {str(e)}'}

    if not subject_id:
         return 400, {'error': 'credentialSubject must contain an "id" or create_did must be True.'}

    return process_credential_issuance(
        request=request,
        schema_name=payload.schema_name,
        subject_data=cleaned_subject,
        credential_type=["VerifiableCredential", "DigitalProductPassport"],
        subject_id=subject_id,
        issuer_did_obj=issuer_did
    )


@api_v1.post("issue-facility/",
response={201: SignedCredentialResponse, 400: ErrorResponse, 403: ErrorResponse, 409: ErrorResponse, 500: ErrorResponse},
             summary="Issue Digital Facility Record",
             auth=DatabaseTokenAuth())
def issue_facility_credential(request, payload: IssueFacilityPayload):

    try:
        issuer_did = resolve_issuer(payload.issuer_did, request.user)
    except ValueError as e:
        return 400, {'error': str(e)}

    cleaned_subject = payload.credentialSubject.copy()
    subject_id = cleaned_subject.get("id")

    if not subject_id and not payload.create_did:
        return 400, {'error': 'credentialSubject must contain an "id" unless create_did is True.'}

   #The facility did is the one used for issuance
    subject_id = issuer_did.did

    return process_credential_issuance(
        request=request,
        schema_name=payload.schema_name,
        subject_data=cleaned_subject,
        credential_type=["VerifiableCredential", "DigitalFacilityRecord"],
        subject_id=subject_id,
        issuer_did_obj=issuer_did
    )

@api_v1.post("issue-traceability/",
             response={201: SignedCredentialResponse, 400: ErrorResponse, 409: ErrorResponse, 500: ErrorResponse},
             summary="Issue Traceability Event Batch",
             auth=DatabaseTokenAuth())
def issue_traceability_credential(request, payload: IssueTraceabilityPayload):

    try:
        issuer_did = resolve_issuer(payload.issuer_did, request.user)
    except ValueError as e:
        return 400, {'error': str(e)}

    events_list = payload.credentialSubject

    if not events_list:
        return 400, {'error': 'credentialSubject must be a non-empty list of events.'}

    first_event_id = events_list[0].get("id")
    if not first_event_id:
        return 400, {'error': 'The first event in the list must have an "id".'}

    return process_credential_issuance(
        request=request,
        schema_name=payload.schema_name,
        subject_data=events_list,
        credential_type=["VerifiableCredential", "DigitalTraceabilityEvent"],
        subject_id=first_event_id,
        issuer_did_obj=issuer_did
    )


def process_credential_issuance(
    request,
    schema_name: str,
    subject_data: Any,
    credential_type: List[str],
    subject_id: str,
    issuer_did_obj
):
    try:
        schema = Schemas.objects.get(file_schema=schema_name)
    except Exception as e:
         return 422, {'error': f"Schema error: {str(e)}"}

    with transaction.atomic():
        # if VerificableCredential.objects.filter(
        #     schema=schema,
        #     issuer_did=issuer_did_obj,
        #     status=VerificableCredential.Status.ISSUED,
        #     subject_id=subject_id
        # ).exists():
        #     return 409, {'error': 'A credential for this subject already exists.'}

        if subject_id and isinstance(subject_data, dict):
            subject_data["id"] = subject_id

        domain = f"https://{settings.DOMAIN}/"
        cred = VerificableCredential(
            verified=True,
            user=request.auth,
            json_data=subject_data,
            subject_id=subject_id,
            issuer_did=issuer_did_obj,
            schema=schema,
        )
        cred.type = credential_type

        verify = not settings.DEBUG
        try:
            rendered_json_str = cred.render(domain)
            valid, error_details = verify_schema(rendered_json_str, verify=verify)

            if not valid:
                return 400, {'error': 'Schema validation failed.', 'details': error_details}

            cred.issue(did=None, domain=domain)
            cred.save()

        except jsonschema.exceptions.ValidationError as e:
            return 400, {'error': 'Schema validation failed.', 'details': e.message, 'path': list(e.path)}
        except Exception as e:
            logger.error(f"Issuance failed: {e}", exc_info=True)
            return 500, {'error': 'Internal server error during credential signing.'}


    signed_credential_str = cred.get_data()
    signed_credential_json = json.loads(signed_credential_str)
    return 201, {"credential": signed_credential_json}

