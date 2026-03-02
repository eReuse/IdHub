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
from .schemas import UpdateServiceEndpointPayload, UpdateServiceEndpointResponse, CreateObjectDIDPayload, CreateObjectDIDResponse, IssueDPPayload, IssueTraceabilityPayload, IssueFacilityPayload, SignedCredentialResponse, ErrorResponse
from idhub.admin.forms import DIDForm
from ninja.security import HttpBearer
from webhook.models import Token
from pyvckit.verify import verify_schema

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
             response={201: CreateObjectDIDResponse, 400: ErrorResponse, 500: ErrorResponse},
             summary="Create a new Object DID",
             auth=DatabaseTokenAuth())
def create_object_did(request, payload: CreateObjectDIDPayload):
    try:
        expected_did = f"did:web:{settings.DOMAIN}:{payload.suffix_did_id}"
        form_data = {
            'label': payload.label or f"device-{payload.suffix_did_id}",
            'type': DID.Types.WEB.value,
            'did': expected_did
        }

        unsaved_instance = DID(type=DID.Types.WEB)
        form = DIDForm(data=form_data, instance=unsaved_instance)

        if not form.is_valid():
            return 400, {
                "error": "Validation failed",
                "details": json.dumps(form.errors.get_json_data())
            }

        form.instance.user = request.user
        form.instance.is_product = True
        form.instance.service_endpoint = payload.service_endpoint

        obj_did = form.save(commit=True)
        doc_json = json.loads(obj_did.didweb_document) if obj_did.didweb_document else {}

        return 201, {
            "did": obj_did.did,
            "did_document": doc_json
        }
    except Exception as e:
        logger.error(f"Failed to create Object DID: {e}", exc_info=True)
        return 500, {"error": "Internal server error during DID creation."}


@api_v1.post("object-did/update/",
             response={200: UpdateServiceEndpointResponse, 403: ErrorResponse, 404: ErrorResponse},
             summary="Update the Service Endpoint of an existing DID",
             auth=DatabaseTokenAuth())
def update_did_service_endpoint(request, payload: UpdateServiceEndpointPayload):

    did_obj = DID.objects.filter(did=payload.did, user=request.user, is_product=True ).first()

    if not did_obj:
        return 404, {"error": "DID not found or you do not have permission to modify it."}

    try:
        did_obj.service_endpoint = payload.service_endpoint
        did_obj.save(update_fields=['service_endpoint', ])

        return 200, {
            "success": True,
            "did": did_obj.did,
            "service_endpoint": did_obj.service_endpoint
        }

    except Exception as e:
        logger.error(f"Failed to update Service Endpoint: {e}", exc_info=True)
        return 500, {"error": "Internal server error updating the DID."}

    

@api_v1.post("issue-dpp/", response={201: SignedCredentialResponse},
             summary="Issue Digital Product Passport", auth=DatabaseTokenAuth())
def issue_dpp_credential(request, payload: IssueDPPayload):
    issuer_did = _find_issuer_did(payload.issuer_did, request.user)

    #only one dpp service_endpoint at a time
    cleaned_subject = payload.credentialSubject.copy()
    subject_did_str = cleaned_subject.get("id")
    did_obj = DID.objects.filter(did=subject_did_str, is_product=True).first()




    return process_credential_issuance(
        request, payload.schema_name, cleaned_subject,
        ["VerifiableCredential", "DigitalProductPassport"],
        did_obj, issuer_did
    )


@api_v1.post("issue-facility/", response={201: SignedCredentialResponse}, summary="Issue Digital Facility Record", auth=DatabaseTokenAuth())
def issue_facility_credential(request, payload: IssueFacilityPayload):
    issuer_did = _find_issuer_did(payload.issuer_did, request.user)

    return process_credential_issuance(
        request, payload.schema_name, payload.credentialSubject,
        ["VerifiableCredential", "DigitalFacilityRecord"],
        #This is self_signing, should another reputable did sign this?
        issuer_did, issuer_did
    )


@api_v1.post("issue-traceability/", response={201: SignedCredentialResponse},
             summary="Issue Traceability Event Batch", auth=DatabaseTokenAuth())
def issue_traceability_credential(request, payload: IssueTraceabilityPayload):
    issuer_did = _find_issuer_did(payload.issuer_did, request.user)
    events_list = payload.credentialSubject

    if not events_list:
        raise ValueError('credentialSubject must be a non-empty list of events.')

    first_event_id = events_list[0].get("id")
    if not first_event_id:
        raise ValueError('The first event in the list must have a valid "id".')

    did_obj = DID.objects.filter(did=first_event_id, is_product=True).first()

    return process_credential_issuance(
        request=request,
        schema_name=payload.schema_name,
        subject_data=events_list,
        credential_type=["VerifiableCredential", "DigitalTraceabilityEvent"],
        subject_did=did_obj,
        issuer_did_obj=issuer_did
    )


def process_credential_issuance(
    request,
    schema_name: str,
    subject_data: Any,
    credential_type: List[str],
    subject_did,
    issuer_did_obj
):
    try:
        schema = Schemas.objects.get(file_schema=schema_name)
    except Schemas.DoesNotExist:
        return 422, {'error': f"Schema '{schema_name}' does not exist."}

    with transaction.atomic():

        domain = f"https://{settings.DOMAIN}/"
        cred = VerificableCredential(
            verified=True, user=request.user, json_data=subject_data,
            issuer_did=issuer_did_obj, schema=schema,
            type= credential_type
        )

        try:
            rendered_json_str = cred.render(domain)
            valid, error_details = verify_schema(rendered_json_str, verify=not settings.DEBUG)

            if not valid:
                return 400, {'error': 'Schema validation failed.', 'details': error_details}

            #For now force usage of subject did, not any other type of id
            cred.issue(did=subject_did if subject_did else None, domain=domain)
            cred.save()

        except jsonschema.exceptions.ValidationError as e:
            return 400, {'error': 'Schema validation failed.', 'details': e.message, 'path': list(e.path)}
        except Exception as e:
            logger.error(f"Issuance failed: {e}", exc_info=True)
            return 500, {'error': 'Internal server error during credential signing.'}

    return 201, {"credential": json.loads(cred.get_data())}
