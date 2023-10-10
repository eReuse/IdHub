from pathlib import Path

import requests
import json

WALLETKITD = 'http://localhost:8080/'
ISSUER = f'{WALLETKITD}issuer-api/default/'
VERIFIER = f'{WALLETKITD}verifier-api/default/'

default_ctype_header = {
    'Content-Type': 'application/json',  # specify the type of data you're sending
    'Accept': 'application/json',  # specify the type of data you can accept
}


def include_str(path):
    with open(path, "r") as f:
        return f.read().strip()


# Create DID for tenant
# Valid methods: 'key'|'web'
def user_create_did(did_method):
    url = f'{ISSUER}config/did/create'
    data = {
        'method': did_method
    }
    response = requests.post(url, json=data, headers=default_ctype_header)
    response.raise_for_status()
    return response.text


def admin_create_template(template_name, template_body):
    url = f'{ISSUER}config/templates/{template_name}'
    body = template_body
    response = requests.post(url, data=body, headers=default_ctype_header)
    response.raise_for_status()
    return


def user_issue_vc(vc_name, vc_params):
    url = f'{ISSUER}credentials/issuance/request'
    # ...
    # TODO examine cross-device issuance workflow
    pass





TENANT_CFG_TMEPLATE = include_str("./TENANT_CFG_TEMPLATE")

