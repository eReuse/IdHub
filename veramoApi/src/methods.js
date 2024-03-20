import { agent } from './setup.js'

export async function verify(credential) {
  const result = await agent.verifyCredential({
    credential: credential
  })
  console.log(`Credential verified`, result.verified)
  return result.verified
}

// verify().catch(console.log)