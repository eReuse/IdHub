const axios = require("axios")
const api_url = "http://localhost:3010"
const route = "oracle"
const params= {
    api_token: "kwgdmnloXyg8XtS.9gELEoE2f8iIJjqt9IVun9BkpQR4enDc4zcDKPQwMzvs1oJPnHVorB9yWVeGbauo",
    Credential: {
        "issuer": {
          "id": "did:ethr:0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F"
        },
        "credentialSubject": {
          "id": "did:ethr:0xf1051D79fA59B580b916418bA699F996edbb25C8",
          "role": "operator"
        },
        "issuanceDate": "2024-03-21T01:00:22.615Z",
        "@context": [
          "https://www.w3.org/2018/credentials/v1"
        ],
        "type": [
          "VerifiableCredential"
        ],
        "proof": {
          "verificationMethod": "did:ethr:0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F#controller",
          "created": "2024-03-21T01:00:22.615Z",
          "proofPurpose": "assertionMethod",
          "type": "EthereumEip712Signature2021",
          "proofValue": "0x6bf99496d6aecfba3440e400dcec0d7fa608d368d7fa830dbd98d33ca2b61daa5f56a78b8fe11c5d86c13aaf5a0c854f758d415a411c29694d1e7a41ba1830c31c",
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