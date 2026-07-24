from ninja import Schema
from typing import Dict, List, Any, Optional

class CreateObjectDIDPayload(Schema):
    suffix_did_id: str
    service_endpoint: Optional[str] = ""
    label: Optional[str] = None

class CreateObjectDIDResponse(Schema):
    did: str
    did_document: Dict[str, Any]

class UpdateServiceEndpointPayload(Schema):
    did: str
    service_endpoint: str

class UpdateServiceEndpointResponse(Schema):
    success: bool
    did: str
    service_endpoint: str

class IssueDPPayload(Schema):
    schema_name: str
    issuer_did: str
    credentialSubject: Dict[str, Any]

class IssueFacilityPayload(Schema):
    schema_name: str
    issuer_did: str
    credentialSubject: Dict[str, Any]

class IssueTraceabilityPayload(Schema):
    schema_name: str
    issuer_did: str
    credentialSubject: List[Dict[str, Any]]

class SignedCredentialResponse(Schema):
    credential: Dict[str, Any]

class ErrorResponse(Schema):
    error: str
    details: Optional[str] = None
    path: Optional[List[str]] = None

class SchemaInfo(Schema):
    name: str
    file_schema: str
    description: Optional[str] = None
    url: Optional[str] = None

class ActiveUNTPSchemasResponse(Schema):
    dpp: List[SchemaInfo]
    dte: List[SchemaInfo]
    dfr: List[SchemaInfo]
