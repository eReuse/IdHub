from ninja import Schema
from typing import Dict, Any, Optional

class IssueCredentialPayload(Schema):
    schema_name: str
    create_did: bool
    credentialSubject: Dict[str, Any]
    service_endpoint: Optional[str] = None

class SignedCredentialResponse(Schema):
    credential: Dict[str, Any]

class ErrorResponse(Schema):
    error: str
    details: str = None
