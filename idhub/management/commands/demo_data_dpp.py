import os
import csv
import json
import logging
import pandas as pd

from pathlib import Path
from utils import credtools
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from pyvckit.did import (
    generate_did,
    gen_did_document,
)

from idhub.models import Schemas, DID, VerificableCredential
from oidc4vp.models import Organization
from idhub.admin.forms import ImportForm
from idhub.user.forms import RequestCredentialForm
from webhook.models import Token


User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Insert minimum data for the project"
    DOMAIN = settings.DOMAIN
    OIDC_ORGS = settings.OIDC_ORGS

    def handle(self, *args, **kwargs):

        # on demo situation, encrypted vault is hardcoded with password DEMO
        cache.set("KEY_DIDS", "DEMO", None)

        # get org
        self.org = Organization.objects.filter(
            name=self.DOMAIN,
            domain=self.DOMAIN,
            main=True
        ).first()

        # get admin@example.org and create dpp did
        self.org = Organization.objects.filter(
            name=self.DOMAIN,
            domain=self.DOMAIN,
            main=True
        ).first()

        # get user1@example.org and create dpp did
        admin_email='admin@example.org'
        self.admin = User.objects.filter(email=admin_email).first()
        self.admin_did = self.create_did()

        self.user1_email='user1@example.org'
        self.user1 = User.objects.filter(email=self.user1_email).first()
        self.user1_did = self.create_did(user=self.user1)

        # override ADMIN_DLT_TOKEN in user1 did to orchestrate with
        #   other dpp services
        API_DLT_OPERATOR_TOKEN = settings.API_DLT_OPERATOR_TOKEN
        key_material = self.user1_did.get_key_material()
        key_material_json = json.loads(key_material)
        key_material_json['eth_api_token'] = API_DLT_OPERATOR_TOKEN
        key_material = json.dumps(key_material_json)
        self.user1_did.set_key_material(key_material)
        self.user1_did.save()

        #   the secret from idhub to devicehub
        self.user1.accept_gdpr=True
        self.user1.save()

        # admin@example.org sends credential import user1@example.org
        cred = self.create_credential()

        # user1@example.org request credential
        cred.issue(self.user1_did, domain=self.DOMAIN)
        cred.call_oracle()
        cred.save()

    def create_did(self, label="dpp", user=None):
        did = DID.objects.create(
            label=label,
            type=DID.Types.WEBETH.value,
            user=user
        )
        did.set_did()
        did.save()
        return did

    def create_credential(self):
        fileschema = 'organization-membership-dlt'
        schema = Schemas.objects.get(file_schema__contains=fileschema)
        row = {'role': 'operator', 'email': self.user1_email}
        cred = VerificableCredential(
            verified=True,
            user=self.user1,
            csv_data=json.dumps(row, default=str),
            issuer_did=self.admin_did,
            schema=schema,
            eidas1_did=None
        )
        cred.set_type()
        cred.save()
        return cred

    def _request_credential(self):
        # TODO user1
        # TODO credential
        fileschema = 'organization-membership-dlt.json'
        schema = Schemas.objects.get(file_schema__contains=fileschema)

        examples = 'examples/excel_examples/'
        name_file = '{}.xlsx'.format(fileschema)
        with Path(__file__).parent.parent.parent.joinpath(examples).joinpath(
                name_file
        ).open('rb') as _f:
                file_content = _f.read()

        uploaded_file = SimpleUploadedFile(name_file, file_content)
        uploaded_file.name = name_file
        self.user1_cred = VerificableCredential.objects.first()

        # Build the form
        form = RequestCredentialForm(
            data = {
                'did': self.user1_did.did,
                'credential': self.user1_cred.id,
                'user': self.user1
            })
        form.is_valid()
        form.save()
