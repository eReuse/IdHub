const axios = require("axios")
const api_url = "http://localhost:3010"
const route = "oracle"
const params= {
    api_token: "jiNQMB6MYc4NUs0.cxyKF6Qd7qsGLATBWVMEkFGmguaDRXPuta0neJlIBgUw7UwZLMALmuW9Qhd3pE7d",
    Credential: {
      "issuer": {
        "id": "did:ethr:0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F"
      },
      "credentialSubject": {
        "id": "did:ethr:0x9689c31ddc9fD8F0Fcb98B7570E82893d9a7E593",
        "role": "operator"
      },
      "issuanceDate": "2024-04-10T08:30:56.318Z",
      "@context": [
        "https://www.w3.org/2018/credentials/v1"
      ],
      "type": [
        "VerifiableCredential"
      ],
      "proof": {
        "verificationMethod": "did:ethr:0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F#controller",
        "created": "2024-04-10T08:30:56.318Z",
        "proofPurpose": "assertionMethod",
        "type": "EthereumEip712Signature2021",
        "proofValue": "0x0fcf812b818a1b6e4a25d4492e86bc76a3b664577962a3a5087f67c83bab627a290c4b1d5b158e126f294ca520ff3c0735a0e070d33e9d464569d6735a4f5c241c",
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