from ninja import Schema
from typing import Dict, List, Any, Optional
from pydantic import Field, HttpUrl

    #TODO: this parameter should be parametrized
    suffix_did_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The unique suffix identifier to be appended to the DID method. This is the identifier part that goes after did:web:example.com:..."
    )
    service_endpoint: Optional[str] = Field(
        "",
        max_length=2048,
        description="The initial service endpoint URL where the product passport can be resolved."
    )
    label: Optional[str] = Field(
        None,
        max_length=255,
        description="An optional human-readable label or internal name for this DID."
    )

class CreateObjectDIDResponse(Schema):
    did: str = Field(
        ...,
        description="The fully resolved Decentralized Identifier (e.g., did:web:example.com:123)."
    )
    did_document: Dict[str, Any] = Field(
        ...,
        description="The complete standard W3C DID Document associated with the created DID."
    )

class UpdateServiceEndpointPayload(Schema):
    did: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="The target Decentralized Identifier to update."
    )
    service_endpoint: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="The new service endpoint URL to associate with this DID."
    )

class UpdateServiceEndpointResponse(Schema):
    success: bool = Field(
        ...,
        description="Indicates whether the endpoint was successfully updated."
    )
    did: str = Field(
        ...,
        description="The Decentralized Identifier that was updated."
    )
    service_endpoint: str = Field(
        ...,
        description="The active service endpoint URL after the update."
    )

class IssueDPPayload(Schema):
    schema_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The specific UNTP Digital Product Passport (DPP) schema identifier to validate against."
    )
    issuer_did: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="The Decentralized Identifier of the entity issuing the passport."
    )
    credentialSubject: Dict[str, Any] = Field(
        ...,
        description="The core payload containing the product attributes."
    )

class IssueFacilityPayload(Schema):
    schema_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The specific UNTP Digital Facility Record (DFR) schema identifier to validate against."
    )
    issuer_did: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="The Decentralized Identifier of the entity issuing the facility credential."
    )
    credentialSubject: Dict[str, Any] = Field(
        ...,
        description="The core payload containing the facility information and attributes."
    )

class IssueTraceabilityPayload(Schema):
    schema_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The specific UNTP Digital Traceability Event (DTE) schema identifier to validate against."
    )
    issuer_did: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="The Decentralized Identifier of the entity issuing the traceability event."
    )
    credentialSubject: List[Dict[str, Any]] = Field(
        ...,
        max_length=1000,
        description="A list of traceability events or lineage data points associated with the product journey."
    )

class SignedCredentialResponse(Schema):
    credential: Dict[str, Any] = Field(
        ...,
        description="The finalized, cryptographically signed Verifiable Credential (VC) in JSON format."
    )

class ErrorResponse(Schema):
    error: str = Field(
        ...,
        description="A brief, machine-readable error code or summary message."
    )
    details: Optional[str] = Field(
        None,
        description="Extended human-readable description of why the error occurred."
    )
    path: Optional[List[str]] = Field(
        None,
        description="The specific location within the JSON payload where a validation error occurred."
    )

class SchemaInfo(Schema):
    name: str = Field(
        ...,
        description="The internal identifier or short name of the schema."
    )
    file_schema: str = Field(
        ...,
        description="The filename or internal path referencing the JSON Schema definition."
    )
    description: Optional[str] = Field(
        None,
        description="A human-readable explanation of what data this schema validates."
    )
    url: Optional[str] = Field(
        None,
        description="The canonical public URL where the schema definition is hosted."
    )

class ActiveUNTPSchemasResponse(Schema):
    dpp: List[SchemaInfo] = Field(
        ...,
        description="List of active schemas for Digital Product Passports (DPP)."
    )
    dte: List[SchemaInfo] = Field(
        ...,
        description="List of active schemas for Digital Traceability Events (DTE)."
    )
    dfr: List[SchemaInfo] = Field(
        ...,
        description="List of active schemas for Digital Facility Records (DFR)."
    )
