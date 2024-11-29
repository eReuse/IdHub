import json
import uuid
import hashlib
import datetime
import logging

from django.core.exceptions import ValidationError
from evidence.xapian import index
from evidence.models import Annotation
from device.models import Device


logger = logging.getLogger('django')


def create_doc(data):
    if not data:
        return
    
    doc = {}
    device = {"manufacturer": "", "model": "", "amount": 1}
    kv = {}
    _uuid = str(uuid.uuid4())
    customer_id = hashlib.sha3_256(_uuid.encode()).hexdigest()


    for k, v in data.items():
        if not v:
            continue
        
        if k.upper() == "CUSTOMER_ID":
            customer_id = v
            continue

        if k.lower() == "type":
            if v not in Device.Types.values:
                raise ValidationError("{} is not a valid device".format(v))

            device["type"] = v
            
        elif k.lower() == "amount":
            try:
                amount = int(v)
                device["amount"] = amount
            except Exception:
                pass

        else:
            kv[k] = v

    if not device:
        return

    doc["device"] = device

    if kv:
        doc["kv"] = kv

    date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    if doc:
        doc["uuid"] = _uuid
        doc["endTime"] = date
        doc["software"] = "DeviceHub"
        doc["CUSTOMER_ID"] = customer_id
        doc["type"] = "WebSnapshot"

    return doc


def create_annotation(doc, user, commit=False):
    if not doc or not doc.get('uuid') or not doc.get("CUSTOMER_ID"):
        return []
    
    data = {
        'uuid': doc['uuid'],
        'owner': user.institution,
        'user': user,
        'type': Annotation.Type.SYSTEM,
        'key': 'CUSTOMER_ID',
        'value': doc['CUSTOMER_ID'],
    }
    if commit:
        annotation = Annotation.objects.filter(
                uuid=doc["uuid"],
                owner=user.institution,
                type=Annotation.Type.SYSTEM,
        )

        if annotation:
            txt = "Warning: Snapshot %s already registered (annotation exists)"
            logger.warning(txt, doc["uuid"])
            return annotation

        return Annotation.objects.create(**data)

    return Annotation(**data)


def create_index(doc, user):
    if not doc or not doc.get('uuid'):
        return []
    
    _uuid = doc['uuid']
    ev = json.dumps(doc)
    index(user.institution, _uuid, ev)
