import { agent } from './veramo/setup.js'

async function main() {
  const identifier = await agent.didManagerGet({ did: 'did:ethr:0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F' })

  const verifiableCredential = await agent.createVerifiableCredential({
    credential: {
      issuer: { id: identifier.did },
      credentialSubject: {
        id: 'did:ethr:0x9689c31ddc9fD8F0Fcb98B7570E82893d9a7E593',
        role: 'operator',
      },
    },
    proofFormat: 'EthereumEip712Signature2021',
  })
  console.error(`New credential created`)
  console.log(JSON.stringify(verifiableCredential, null, 2))
}

main().catch(console.log)
