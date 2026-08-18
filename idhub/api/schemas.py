from ninja import Schema
from typing import Dict, List, Any, Optional
from pydantic import Field, HttpUrl


class BaseIssuePayload(Schema):
    """
    base schema for all untps credencial issuance requests
    """
    schema_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The specific UNTP schema identifier (e.g., DPP, DFR, DTE) to validate against."
    )
    issuer_did: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="The Decentralized Identifier of the entity issuing this credential."
    )


class DIDEndpointBase(Schema):
    """
    base schema for service endpoint
    """
    did: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="The target Decentralized Identifier."
    )
    service_endpoint: HttpUrl = Field(
        ...,
        description="The service endpoint URL associated with this DID."
    )


class CreateObjectDIDPayload(Schema):
    suffix_did_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The unique suffix identifier to be appended to the DID method."
    )
    service_endpoint: Optional[HttpUrl] = Field(
        None,
        description="The initial service endpoint URL where the product passport can be resolved."
    )
    label: Optional[str] = Field(
        None,
        max_length=255,
        description="An optional human-readable label or internal name for this DID."
    )


class CreateObjectDIDResponse(Schema):
    did: str = Field(..., description="The fully resolved Decentralized Identifier.")
    did_document: Dict[str, Any] = Field(..., description="The standard W3C DID Document.")


class UpdateServiceEndpointPayload(DIDEndpointBase):
    pass


class UpdateServiceEndpointResponse(DIDEndpointBase):
    success: bool = Field(
        ...,
        description="Indicates whether the endpoint was successfully updated."
    )


class IssueDPPayload(BaseIssuePayload):
    credentialSubject: Dict[str, Any] = Field(
        ...,
        description="The core payload containing the product passport (DPP) attributes."
    )


class IssueFacilityPayload(BaseIssuePayload):
    credentialSubject: Dict[str, Any] = Field(
        ...,
        description="The core payload containing the facility (DFR) information and attributes."
    )


class IssueTraceabilityPayload(BaseIssuePayload):
    credentialSubject: List[Dict[str, Any]] = Field(
        ...,
        max_length=1000,
        description="A list of traceability events (DTE) associated with the product journey."
    )


class SignedCredentialResponse(Schema):
    credential: Dict[str, Any] = Field(
        ...,
        description="The finalized, cryptographically signed Verifiable Credential (VC)."
    )


class ErrorResponse(Schema):
    error: str = Field(..., description="A brief, machine-readable error code.")
    details: Optional[str] = Field(None, description="Extended human-readable error description.")
    path: Optional[List[str]] = Field(None, description="The specific location within the JSON payload where validation failed.")


class SchemaInfo(Schema):
    name: str = Field(..., description="The internal identifier or short name of the schema.")
    file_schema: str = Field(..., description="The filename or internal path referencing the JSON Schema.")
    description: Optional[str] = Field(None, description="Explanation of what data this schema validates.")
    url: Optional[HttpUrl] = Field(None, description="Canonical public URL for the schema definition.")


class ActiveUNTPSchemasResponse(Schema):
    dpp: List[SchemaInfo] = Field(..., description="List of active schemas for Digital Product Passports (DPP).")
    dte: List[SchemaInfo] = Field(..., description="List of active schemas for Digital Traceability Events (DTE).")
    dfr: List[SchemaInfo] = Field(..., description="List of active schemas for Digital Facility Records (DFR).")
