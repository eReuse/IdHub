import { TKeyType } from '@veramo/core'
import { agent } from './veramo/setup.js'

async function main() {
  const key = {
    kms:"local",
    privateKeyHex: "0x807118c237e01677f0522f9ca50535b1984481ea2e09115197934a9cd73ab8c1",
    type: 'Secp256k1' as TKeyType,
    publicKeyHex: '0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F'
  }

  const identifier = await agent.didManagerImport({
    keys: [key],
    provider: "did:ethr",
    did: "did:ethr:0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F"
  })
  console.log(`New identifier created`)
  console.log(JSON.stringify(identifier, null, 2))
}

main().catch(console.log)