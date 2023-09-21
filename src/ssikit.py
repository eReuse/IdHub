import requests
import json

CUSTODIAN = 'http://localhost:7002'
SIGNATORY = 'http://localhost:7001'
AUDITOR = 'http://localhost:7003'

CORE = 'http://localhost:7000'
ESSIF = 'http://localhost:7004'

PROOF_TYPE = 'LD_PROOF' # Specifies the format and cryptographic algorithm used for the digital signature of the Verifiable Credential. E.g. LD_PROOF
STATUS_TYPE = 'StatusList2021Entry' # Specifies if the credential should be issued with status and the type of the status. Options StatusList2021Entry or SimpleCredentialStatus2022

jsonheaders = {
    'Content-Type': 'application/json',  # specify the type of data you're sending
    'Accept': 'application/json',  # specify the type of data you can accept
}

jsontextheaders = {
    'Content-Type': 'application/json',  # specify the type of data you're sending
    'Accept': 'text/plain',  # specify the type of data you can accept
}

def check_backend_service():
    url = f'{CUSTODIAN}/'
    try:
        response = requests.get(url)
        # response.raise_for_status()
    except requests.exceptions.RequestException:
        raise ImportError("Local backend service not responding")

# check_backend_service()

def debug_http(): 
    import logging

    # internet search:
    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

def create_did(method):
    url = f'{CUSTODIAN}/did/create'
    data = {
      'method': method
    }
    response = requests.post(url, json=data, headers=jsonheaders)
    return response.text
    #return response.status_code

# print(create_did('key'))
issuer_id = 'did:key:z6MkjAkDgMGxBFbAvUP5snkhz9WDDVQ5uVDwHR88ykAiMfNF'
subject_id = 'did:key:z6MkjtArtcgMSgV8aBdbFCFETqhFanLVRXcQPs7BeXyF5wdL'

default_alg = 'EdDSA_Ed25519'

def generate_key(alg=default_alg):
    url = f'{CUSTODIAN}/keys/generate'
    data = {
      'keyAlgorithm': alg
    }
    # print(data)
    response = requests.post(url, json=data, headers=jsonheaders)
    return response.json()
    #return response.status_code

# print('generate_key: ' + json.dumps(generate_key()))

def list_templates():
    url = f'{SIGNATORY}/v1/templates'

    response = requests.get(url, headers=jsonheaders)
    #print(response.status_code)
    return response.text

# print(list_templates())

def import_template(id, template):
    url = f'{SIGNATORY}/v1/templates/' + id

    response = requests.post(url, json=json.loads(template), headers=jsontextheaders)
    print(response.text)
    return response.status_code
    #return response.text

default_template='EmployeeID'

# print('Import template: ', import_template('EmployeeID','{"type":["VerifiableCredential","EmployeeID"],"credentialSubject":{"id":"","name":"","role":"","joiningDate":""}}'))

def issue_vc(issuer, subject, template, cdata):
    url = f'{SIGNATORY}/v1/credentials/issue'
    jls_extract_var = cdata
    body = {
      'templateId': template,
      'config': {
        'issuerDid': issuer,
        'subjectDid': subject,
        'proofType': PROOF_TYPE, 
        'statusType': STATUS_TYPE
        },
        'credentialData': cdata
    }

    print(body)
    response = requests.post(url, json=body, headers=jsonheaders)
    return response.json()
    #return response.text

default_cdata = json.loads('{"name":"Emma","role":"Engineer","joiningDate":"2023-06-28"}')

# {'templateId': 'EmployeeID', 'config': {'issuerDid': 'did:key:z6MkjAkDgMGxBFbAvUP5snkhz9WDDVQ5uVDwHR88ykAiMfNF', 'subjectDid': 'did:key:z6MkjtArtcgMSgV8aBdbFCFETqhFanLVRXcQPs7BeXyF5wdL', 'proofType': 'LD_PROOF', 'statusType': 'StatusList2021Entry'}, 'credentialData': {'name': 'Emma', 'role': 'Engineer', 'joiningDate': '2023-06-28'}}
# print('Issue VC: ', json.dumps(issue_vc(issuer_id, subject_id, default_template, default_cdata)))
# Note: issue when generating the credential, returns revocation and credential has some errors

if __name__ == "__main__":
    check_backend_service()
    print("Main: Check comments for testing calls")
else:
    check_backend_service()