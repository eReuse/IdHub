import json
import logging

from ninja import NinjaAPI

from webhook.models import Token
from ninja.security import HttpBearer
from idhub.models import DID, Schemas
from django.core.exceptions import PermissionDenied
from idhub.services import CredentialIssuanceService, DIDService
from .schemas import (
    ActiveUNTPSchemasResponse,
    UpdateServiceEndpointPayload,
    UpdateServiceEndpointResponse,
    CreateObjectDIDPayload,
    CreateObjectDIDResponse,
    IssueDPPayload,
    IssueTraceabilityPayload,
    IssueFacilityPayload,
    SignedCredentialResponse,
    ErrorResponse
)


api_v1 = NinjaAPI(version='1.0.0', title="IdHub v1 API")

logger = logging.getLogger(__name__)

@api_v1.exception_handler(ValueError)
def handle_value_error(request, exc):
    return api_v1.create_response(request, {"error": str(exc)}, status=400)

@api_v1.exception_handler(PermissionDenied)
def handle_permission_denied(request, exc):
    return api_v1.create_response(request, {"error": str(exc)}, status=403)


class DatabaseTokenAuth(HttpBearer):
    def authenticate(self, request, token_string):
        try:
            token_obj = Token.objects.select_related('owner').get(
                token=token_string, active=True
            )
            request.user = token_obj.owner
            return request.user
        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            return None


def _find_issuer_did(requested_did: str, user):
    if not requested_did:
        raise ValueError(f"Requested Issuer DID '{requested_did}' not found on this server.")

    issuer = DID.objects.filter(did=requested_did, user__isnull=True, is_product=False).first()
    if not issuer:
        raise PermissionDenied(f"You do not own the Issuer DID '{requested_did}' or it doesnt exist.")
    return issuer


@api_v1.post("object-did/create/",
             response={200: CreateObjectDIDResponse, 201: CreateObjectDIDResponse, 400: ErrorResponse, 500: ErrorResponse},
             summary="Create a new Object DID",
             auth=DatabaseTokenAuth())
def create_object_did(request, payload: CreateObjectDIDPayload):
    try:
        obj_did, created = DIDService.get_or_create_product_did(
            user=request.user,
            did_type=DID.Types.WEB.value,
            label=payload.label or f"device-{payload.suffix_did_id}",
            service_endpoint=str(payload.service_endpoint) if payload.service_endpoint else None,
            suffix_did_id=payload.suffix_did_id
        )

        doc_json = json.loads(obj_did.didweb_document) if obj_did.didweb_document else {}
        status_code = 201 if created else 200

        return status_code, {
            "did": obj_did.did,
            "did_document": doc_json,
            "service_endpoint": str(payload.service_endpoint) if payload.service_endpoint else None
        }

    except Exception as e:
        logger.error(f"Failed to create Object DID: {e}", exc_info=True)
        return 500, {"error": "Internal server error during DID creation."}


@api_v1.post("object-did/update/",
             response={200: UpdateServiceEndpointResponse, 403: ErrorResponse, 404: ErrorResponse},
             summary="Update the Service Endpoint of an existing DID",
             auth=DatabaseTokenAuth())
def update_did_service_endpoint(request, payload: UpdateServiceEndpointPayload):

    did_obj = DID.objects.filter(did=payload.did, user=request.user, is_product=True).first()

    if not did_obj:
        return 404, {"error": "DID not found or you do not have permission to modify it."}

    try:
        endpoint_str = str(payload.service_endpoint) if payload.service_endpoint else ""
        did_obj.service_endpoint = endpoint_str

        DIDService.sync_endpoint_to_document(did_obj)
        did_obj.save(update_fields=['service_endpoint', 'didweb_document'])

        return 200, {
            "success": True,
            "did": did_obj.did,
            "service_endpoint": endpoint_str
        }

    except Exception as e:
        logger.error(f"Failed to update Service Endpoint: {e}", exc_info=True)
        return 500, {"error": "Internal server error updating the DID."}


@api_v1.post("issue-dpp/",
             response={201: SignedCredentialResponse, 400: ErrorResponse, 422: ErrorResponse, 500: ErrorResponse},
             summary="Issue Digital Product Passport", auth=DatabaseTokenAuth())
def issue_dpp_credential(request, payload: IssueDPPayload):
    issuer_did = _find_issuer_did(payload.issuer_did, request.user)

    # only one dpp service_endpoint at a time
    cleaned_subject = payload.credentialSubject.copy()
    subject_did_str = cleaned_subject.get("id")
    did_obj = DID.objects.filter(did=subject_did_str, is_product=True).first()

    status_code, response_data = CredentialIssuanceService.issue_untp_credential(
        user=request.user,
        schema_name=payload.schema_name,
        subject_data=cleaned_subject,
        credential_type=["VerifiableCredential", "DigitalProductPassport"],
        subject_did=did_obj,
        issuer_did_obj=issuer_did
    )
    return status_code, response_data


@api_v1.post("issue-facility/",
    response={201: SignedCredentialResponse, 400: ErrorResponse, 422: ErrorResponse, 500: ErrorResponse},
    summary="Issue Digital Facility Record", auth=DatabaseTokenAuth())
def issue_facility_credential(request, payload: IssueFacilityPayload):
    issuer_did = _find_issuer_did(payload.issuer_did, request.user)

    status_code, response_data = CredentialIssuanceService.issue_untp_credential(
        user=request.user,
        schema_name=payload.schema_name,
        subject_data=payload.credentialSubject,
        credential_type=["VerifiableCredential", "DigitalFacilityRecord"],
        subject_did=issuer_did, # This is self_signing
        issuer_did_obj=issuer_did
    )
    return status_code, response_data


@api_v1.post("issue-traceability/",
    response={201: SignedCredentialResponse, 400: ErrorResponse, 422: ErrorResponse, 500: ErrorResponse},
    summary="Issue Traceability Event Batch", auth=DatabaseTokenAuth())
def issue_traceability_credential(request, payload: IssueTraceabilityPayload):
    issuer_did = _find_issuer_did(payload.issuer_did, request.user)
    events_list = payload.credentialSubject

    # Improved Validation: Return standard 400 errors instead of crashing the thread with unhandled ValueErrors
    if not events_list or not isinstance(events_list, list):
        return 400, {"error": "credentialSubject must be a non-empty list of events."}

    first_event_id = events_list[0].get("id")
    if not first_event_id:
        return 400, {"error": 'The first event in the list must have a valid "id".'}

    did_obj = DID.objects.filter(did=first_event_id, is_product=True).first()

    status_code, response_data = CredentialIssuanceService.issue_untp_credential(
        user=request.user,
        schema_name=payload.schema_name,
        subject_data=events_list,
        credential_type=["VerifiableCredential", "DigitalTraceabilityEvent"],
        subject_did=did_obj,
        issuer_did_obj=issuer_did
    )
    return status_code, response_data


@api_v1.get("schemas/untp/active/", response=ActiveUNTPSchemasResponse, auth=DatabaseTokenAuth(),  summary="Get active UNTP schemas")
def get_active_schemas(request):
    """
    Returns ONLY active schemas that are strictly compliant with the UNTP standard.
    """
    all_schemas = Schemas.objects.all()

    response_data = {
        "dpp": [],
        "dte": [],
        "dfr": []
    }

    for schema in all_schemas:
        untp_type = schema.is_untp

        if not untp_type:
            continue

        schema_info = {
            "name": schema.file_schema,
            "file_schema": schema.file_schema,
            "description": schema._description,
            "url": schema.validation_url
        }

        if untp_type == "DigitalProductPassport":
            response_data["dpp"].append(schema_info)
        elif untp_type == "DigitalTraceabilityEvent":
            response_data["dte"].append(schema_info)
        elif untp_type == "DigitalFacilityRecord":
            response_data["dfr"].append(schema_info)

    return response_data
