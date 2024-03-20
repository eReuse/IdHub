import { agent } from './veramo/setup.js'

async function main() {
  const identifier = await agent.didManagerGet({ did: 'did:ethr:0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F' })

  const verifiableCredential = await agent.createVerifiableCredential({
    credential: {
      issuer: { id: identifier.did },
      credentialSubject: {
        id: 'did:ethr:0x7b0D35490f5245b93b5bd832F71e6a32055cFaaC',
        role: 'operator',
      },
    },
    proofFormat: 'EthereumEip712Signature2021',
  })
  console.log(`New credential created`)
  console.log(JSON.stringify(verifiableCredential, null, 2))
}

main().catch(console.log)