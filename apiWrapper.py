import requests
import sys

class API:
    def __init__(self, endpoint, key, dlt):
        self.api_endpoint = endpoint
        self.api_key = key
        self.dlt = {'dlt' : dlt}

    def change_api_key(self, newKey):
        self.api_key = newKey

    def make_post(self, endpoint, payload, headers):
        path = self.api_endpoint + endpoint
        res = requests.post(path, data=payload, headers=headers)
        return res

    def make_get(self, endpoint, parameters, headers):
        path = self.api_endpoint + endpoint
        res = requests.get(path, params=parameters, headers=headers)
        return res

    def invalidate_user(self):
        params = {
            'api_token' : self.api_key
        }
        res = self.make_post("/invalidateUser", params, self.dlt)
        return res.content

    def set_issuer(self, target):
        params = {
            'api_token' : self.api_key,
            'target_user' : target
        }
        res = self.make_post("/setIssuer", params, self.dlt)
        return res.content

    def issue_credential(self, credential, target):
        params = {
            'api_token' : self.api_key,
            'CredentialType' : credential,
            'target_user' : target
        }
        res = self.make_post("/issueCredential", params, self.dlt)
        return res.content
    
    def register_device(self, deviceCHID):
        params = {
            'api_token' : self.api_key,
            'DeviceCHID' : deviceCHID
        }
        res = self.make_post("/registerDevice", params, self.dlt)
        return res.content

    def deRegister_device(self, deviceCHID):
        params = {
            'api_token' : self.api_key,
            'DeviceCHID' : deviceCHID
        }
        res = self.make_post("/deRegisterDevice", params, self.dlt)
        return res.content
   

    def issue_passport(self, deviceDPP, docID, docSig, issuerID):
        params = {
            'api_token' : self.api_key,
            'DeviceDPP' : deviceDPP,
            'DocumentID' : docID,
            'DocumentSignature' : docSig,
            'IssuerID' : issuerID
        }
        res = self.make_post("/issuePassport", params, self.dlt)
        return res.content

    def generate_proof(self, deviceCHID, docID, docSig, issuerID, type):
        params = {
            'api_token' : self.api_key,
            'DeviceCHID' : deviceCHID,
            'DocumentID' : docID,
            'DocumentSignature' : docSig,
            'IssuerID' : issuerID,
            'Type' : type
        }
        res = self.make_post("/generateProof", params, self.dlt)
        return res.content
    
    def get_register_proof(self, deviceCHID):
        params = {
            'api_token' : self.api_key,
            'DeviceCHID' : deviceCHID
        }
        res = self.make_post("/getRegisterProofsByCHID", params, self.dlt)
        return res.content

    def get_issue_proofs(self, deviceCHID):
        params = {
            'api_token' : self.api_key,
            'DeviceCHID' : deviceCHID
        }
        res = self.make_post("/getIssueProofs", params, self.dlt)
        return res.content

    def get_generic_proofs(self, deviceCHID):
        params = {
            'api_token' : self.api_key,
            'DeviceCHID' : deviceCHID
        }
        res = self.make_post("/getProofs", params, self.dlt)
        return res.content

    def check_user_roles(self):
        params = {
            'api_token' : self.api_key,
        }
        res = self.make_post("/checkUserRoles", params, self.dlt)
        return res.content

    def get_did_data(self, deviceCHID):
        params = {
            'api_token' : self.api_key,
            'DeviceCHID' : deviceCHID
        }
        res = self.make_post("/getDidData", params, self.dlt)
        return res.content

    def add_service(self, deviceCHID, type, endpoint, desc, frag):
        params = {
            'api_token' : self.api_key,
            'DeviceCHID' : deviceCHID,
            'Type' : type,
            'endpoint' : endpoint,
            'description' : desc,
            'fragment' : frag
        }
        res = self.make_post("/getDidData", params, self.dlt)
        return res.content

    def remove_service(self, deviceCHID, frag):
        params = {
            'api_token' : self.api_key,
            'DeviceCHID' : deviceCHID,
            'fragment' : frag
        }
        res = self.make_post("/removeService", params, self.dlt)
        return res.content


# if (len(sys.argv) <= 1):
#     raise Exception("Please specify api_key")


def register_user(endpoint, privateKey = ""):
    payload = {
        'privateKey' : privateKey
    }
    res = requests.post(endpoint + "/registerUser", data=payload)
    return res

# def invalidate_user(api_token, dlt):
#     headers = {'dlt' : dlt}
#     params = {
#         'api_token' : api_token
#     }
#     res = make_post("/invalidateUser", params, headers)
#     return res


# def make_post(endpoint, payload, headers):
#     path = 'http://localhost:' + port + endpoint
#     r = requests.post(path, data=payload, headers=headers)
#     return r

# def make_get(endpoint, parameters, headers):
#     path = 'http://localhost:' + port + endpoint
#     print (path)
#     print (headers)
#     r = requests.post(path, params=parameters, headers=headers)
#     return r




# def register_device():
#     print("test")

# def issue_Passport():
#     print("test")


