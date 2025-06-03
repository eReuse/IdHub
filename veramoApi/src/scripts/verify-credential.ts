import { agent } from './veramo/setup.js'

const CHAIN_ID = process.env.CHAIN_ID

async function main() {
  const result = await agent.verifyCredential({
    credential: {
      "issuer": {
        "id": "did:ethr:0x25F36B8BC7431135756F8774D58daeb5FEA8f9F2"
      },
      "credentialSubject": {
        "id": "did:ethr:0x25F36B8BC7431135756F8774D58daeb5FEA8f9F2",
        "role": "operator"
      },
      "issuanceDate": "2024-01-16T07:59:44.394Z",
      "@context": [
        "https://www.w3.org/2018/credentials/v1"
      ],
      "type": [
        "VerifiableCredential"
      ],
      "proof": {
        "verificationMethod": "did:ethr:0x25F36B8BC7431135756F8774D58daeb5FEA8f9F2#controller",
        "created": "2024-01-16T07:59:44.394Z",
        "proofPurpose": "assertionMethod",
        "type": "EthereumEip712Signature2021",
        "proofValue": "0xc591b2f526ad842a91f730543bf70f5143b61f55a53e630beab2f7fac9cf97f616bc6eb9edb0f73f95e1d21ba39e1d5abb423d12c486fb5612e460b8a546818e1c",
        "eip712": {
          "domain": {
            "chainId": CHAIN_ID,
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
    },
  })
  console.log(`Credential verified`, result.verified)
}

main().catch(console.log)
