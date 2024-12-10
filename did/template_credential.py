dpp_tmpl = {
  "@context": [
    "https://www.w3.org/ns/credentials/v2",
    "https://test.uncefact.org/vocabulary/untp/dpp/0.5.0/"
  ],
  "type": [
    "DigitalProductPassport",
    "VerifiableCredential"
  ],
  "id": "https://example.ereuse.org/credentials/2a423366-a0d6-4855-ba65-2e0c926d09b0",
  "issuer": {
    "type": [
      "CredentialIssuer"
    ],
    "id": "did:web:r1.identifiers.ereuse.org:did-registry:z6Mkoreij5y9bD9fL5SGW6TfMUmcbaV7LCPwZHCFEEZBrVYQ#z6Mkoreij5y9bD9fL5SGW6TfMUmcbaV7LCPwZHCFEEZBrVYQ",
    "name": "Refurbisher One"
  },
  "validFrom": "2024-11-15T12:00:00",
  "validUntil": "2034-11-15T12:00:00",
  "credentialSubject": {
    "type": [
      "Product"
    ],
    "id": "https://id.ereuse.org/01/09520123456788/21/12345",
    "name": "Refurbished XYZ Lenovo laptop item",
    "registeredId": "09520123456788.21.12345",
    "description": "XYZ Lenovo laptop refurbished by Refurbisher One",
    "data": ""
  },
  "credentialSchema": {
    "id": "https://idhub.pangea.org/vc_schemas/dpp.json",
    "type": "FullJsonSchemaValidator2021",
    "proof": {
      "type": "Ed25519Signature2018",
      "proofPurpose": "assertionMethod",
      "verificationMethod": "did:web:r1.identifiers.ereuse.org:did-registry:z6Mkoreij5y9bD9fL5SGW6TfMUmcbaV7LCPwZHCFEEZBrVYQ#z6Mkoreij5y9bD9fL5SGW6TfMUmcbaV7LCPwZHCFEEZBrVYQ",
      "created": "2024-12-03T15:33:42Z",
      "jws": "eyJhbGciOiJFZERTQSIsImNyaXQiOlsiYjY0Il0sImI2NCI6ZmFsc2V9..rBPqbOcZCXB7GAnq1XIfV9Jvw4MKXlHff7qZkRfgwQ0Hnd9Ujt5s1xT4O0K6VESzWvdP2mOvMvu780fVNfraBQ"
    }
  }
}
