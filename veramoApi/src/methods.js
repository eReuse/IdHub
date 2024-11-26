import { agent } from './setup.js'
import { execSync } from 'child_process';

export async function verify(credential) {
  // TODO replace with pyvckit
  //const result = execSync('python /path/to/pyvckit-script.py').toString().trim();
  const result = await agent.verifyCredential({
    credential: credential
  })
  console.log(`Credential verified`, result.verified)
  return result.verified
}

// verify().catch(console.log)
