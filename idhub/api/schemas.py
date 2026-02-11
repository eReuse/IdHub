from ninja import Schema
from typing import Dict, List, Any, Optional


class IssueDPPayload(Schema):
    schema_name: str
    create_did: bool = False
    subject_did_suffix: Optional[str] = None
    issuer_did: str
    service_endpoint: Optional[str] = None
    credentialSubject: Dict[str, Any]

class IssueFacilityPayload(Schema):
    schema_name: str
    issuer_did: str
    credentialSubject: Dict[str, Any]

class IssueTraceabilityPayload(Schema):
    schema_name: str
    subject_did_suffix: str
    issuer_did: str
    credentialSubject: List[Dict[str, Any]]

class SignedCredentialResponse(Schema):
    credential: Dict[str, Any]

class ErrorResponse(Schema):
    error: str
    details: Optional[str] = None
    path: Optional[List[str]] = None
