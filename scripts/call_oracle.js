const axios = require("axios")
const api_url = "http://localhost:3010"
const route = "oracle"
const params= {
    api_token: "ZxA4dzZBE2gKNpW.iE0PoareeotjWZN0RSAv6QoeGClhbNrfYwvdtbOsOcC3VYmdls8GgktkE8O8nJeQ",
    Credential: {
      "issuer": {
        "id": "did:ethr:0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F"
      },
      "credentialSubject": {
        "id": "did:ethr:0xf1051D79fA59B580b916418bA699F996edbb25C8",
        "role": "operator"
      },
      "issuanceDate": "2024-04-19T08:04:54.723Z",
      "@context": [
        "https://www.w3.org/2018/credentials/v1"
      ],
      "type": [
        "VerifiableCredential"
      ],
      "proof": {
        "verificationMethod": "did:ethr:0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F#controller",
        "created": "2024-04-19T08:04:54.723Z",
        "proofPurpose": "assertionMethod",
        "type": "EthereumEip712Signature2021",
        "proofValue": "0xe721e07e161d2f137918b3673dc1f925bcdd734b259fc1b7d2a9349c31a3f75c60b5b4472df00d9f8434db457ef26808b3c36993606185462af9f2a71cd5d1cf1b",
        "eip712": {
          "domain": {
            "chainId": 457,
            "name": "VerifiableCredential",
            "version": "1"
          },
          "types": {
            "EIP712Domain": [
              {
                "name": "name",
                "type": "string"
              },
              {
                "name": "version",
                "type": "string"
              },
              {
                "name": "chainId",
                "type": "uint256"
              }
            ],
            "CredentialSubject": [
              {
                "name": "id",
                "type": "string"
              },
              {
                "name": "role",
                "type": "string"
              }
            ],
            "Issuer": [
              {
                "name": "id",
                "type": "string"
              }
            ],
            "Proof": [
              {
                "name": "created",
                "type": "string"
              },
              {
                "name": "proofPurpose",
                "type": "string"
              },
              {
                "name": "type",
                "type": "string"
              },
              {
                "name": "verificationMethod",
                "type": "string"
              }
            ],
            "VerifiableCredential": [
              {
                "name": "@context",
                "type": "string[]"
              },
              {
                "name": "credentialSubject",
                "type": "CredentialSubject"
              },
              {
                "name": "issuanceDate",
                "type": "string"
              },
              {
                "name": "issuer",
                "type": "Issuer"
              },
              {
                "name": "proof",
                "type": "Proof"
              },
              {
                "name": "type",
                "type": "string[]"
              }
            ]
          },
          "primaryType": "VerifiableCredential"
        }
      }
    }
  }    
const dlt = "ethereum"
axios.post(`${api_url}/${route}`, params, {
    headers: {
        dlt: dlt
    }
}).then(data => {
    console.log(data)
}
    
)