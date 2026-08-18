from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

class CredentialSchema(BaseModel):
    type: str = "FullJsonSchemaValidator2021"
    id: str


class IssuerV0(BaseModel):
    type: List[str] = ["CredentialIssuer"]
    id: str
    name: str

    issuerAlsoKnownAs: Optional[List[str]] = None


class UNTPCredentialV0(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    context: List[str] = Field(alias="@context")
    type: List[str]
    id: str
    name: str = "Idhub UNTP 0.7.0  credential"
    issuer: IssuerV0
    validFrom: str

    credentialSubject: Union[Dict[str, Any], List[Dict[str, Any]]]
    credentialSchema: CredentialSchema
