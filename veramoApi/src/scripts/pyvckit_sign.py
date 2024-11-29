import json
import datetime

from pyvckit.did import generate_keys, generate_did
from pyvckit.sign_vc import sign


key = generate_keys()
did = generate_did(key)

cred = {
  "@context": [
    "https://www.w3.org/2018/credentials/v1"
  ],
  "type": [
    "VerifiableCredential"
  ],
    "issuer": "{}".format(did),
  "issuanceDate": "{}".format(datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")),
  "credentialSubject": {
    "id": "0x9689c31ddc9fD8F0Fcb98B7570E82893d9a7E593",
    "issuer_id": "0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F",
    "role": "operator"
  }
}

credential = json.dumps(cred)

print(json.dumps(sign(credential, key, did)))
