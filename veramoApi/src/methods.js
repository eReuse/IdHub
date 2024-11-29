import { agent } from './setup.js'
import { execSync } from 'child_process';

export async function verify(credential) {
  const result = execSync('python scripts/pyvckit_verify.py ../shared/pyvckit-api_credential.json').toString().trim();
  console.log(`Credential verified`, result)
  return result == 'True'
}

// verify().catch(console.log)
