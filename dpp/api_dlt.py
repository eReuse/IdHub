import time
import logging

from django.conf import settings
from ereuseapi.methods import API

from dpp.models import Proof


logger = logging.getLogger('django')


# """The code of the status response of api dlt."""
STATUS_CODE = {
    "Success": 201,
    "Notwork": 400
}


ALGORITHM = "sha3-256"


PROOF_TYPE = {
    'Register': 'Register',
    'IssueDPP': 'IssueDPP',
    'proof_of_recycling': 'proof_of_recycling',
    'Erase': 'Erase',
    'EWaste': 'EWaste',
}


def connect_api():

    if not settings.TOKEN_DLT:
        return

    token_dlt = settings.TOKEN_DLT
    api_dlt = settings.API_DLT

    return API(api_dlt, token_dlt, "ethereum")


def register_dlt(chid, phid, proof_type=None):
    api = connect_api()
    if not api:
        return

    if proof_type:
        return api.generate_proof(
            chid,
            ALGORITHM,
            phid,
            proof_type,
            settings.ID_FEDERATED
        )

    return api.register_device(
        chid,
        ALGORITHM,
        phid,
        settings.ID_FEDERATED
    )


def issuer_dpp_dlt(dpp):
    phid = dpp.split(":")[0]
    api = connect_api()
    if not api:
        return

    return api.issue_passport(
        dpp,
        ALGORITHM,
        phid,
        settings.ID_FEDERATED
    )



def save_proof(signature, ev_uuid, result, proof_type, user):
    if result['Status'] == STATUS_CODE.get("Success"):
        timestamp = result.get('Data', {}).get('data', {}).get('timestamp')

        if not timestamp:
            return

        d = {
            "type": proof_type,
            "timestamp": timestamp,
            "issuer": user.institution.id,
            "user": user,
            "uuid": ev_uuid,
            "signature": signature,
        }
        Proof.objects.create(**d)


def register_device_dlt(chid, phid, ev_uuid, user):
    token_dlt = settings.TOKEN_DLT
    api_dlt = settings.API_DLT
    if not token_dlt or not api_dlt:
        return
    
    cny_a = 1
    while cny_a:
        result = register_dlt(chid, phid)
        try:
            assert result['Status'] == STATUS_CODE.get("Success")
            assert result['Data']['data']['timestamp']
            cny_a = 0
        except Exception:
            if result.get("Data") != "Device already exists":
                logger.error("API return: %s", result)
                time.sleep(10)
            else:
                cny_a = 0

    save_proof(phid, ev_uuid, result, PROOF_TYPE['Register'], user)


    # TODO is neccesary?
    # if settings.get('ID_FEDERATED'):
    #     cny = 1
    #     while cny:
    #         try:
    #             api.add_service(
    #                 chid,
    #                 'DeviceHub',
    #                 settings.get('ID_FEDERATED'),
    #                 'Inventory service',
    #                 'Inv',
    #             )
    #             cny = 0
    #         except Exception:
    #             time.sleep(10)


def register_passport_dlt(chid, phid, ev_uuid, user):
    token_dlt = settings.TOKEN_DLT
    api_dlt = settings.API_DLT
    if not token_dlt or not api_dlt:
        return
    
    dpp = "{chid}:{phid}".format(chid=chid, phid=phid)
    if Proof.objects.filter(signature=dpp, type=PROOF_TYPE['IssueDPP']).exists():
        return

    cny_a = 1
    while cny_a:
        try:
            result = issuer_dpp_dlt(dpp)
            cny_a = 0
        except Exception as err:
            logger.error("ERROR API issue passport return: %s", err)
            time.sleep(10)

    if result['Status'] is not STATUS_CODE.get("Success"):
        logger.error("ERROR API issue passport return: %s", result)
        return
    
    save_proof(phid, ev_uuid, result, PROOF_TYPE['IssueDPP'], user)
