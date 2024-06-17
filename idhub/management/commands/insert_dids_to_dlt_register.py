import requests

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from idhub.models import Schemas, DID


User = get_user_model()


class Command(BaseCommand):
    help = "Insert in dlt register pairs of did:schema_id"

    def handle(self, *args, **kwargs):
        self.save_in_verificable_register()

    def save_in_verificable_register(self):
        if not settings.API_TOKEN:
            return

        for did in DID.objects.filter(user__isnull=True):
            hashes = self.get_verificable_register(did)
            for schema in Schemas.objects.all():
                schema_id = schema.get_id()
                if not schema_id in settings.RESTRICTED_ISSUANCE_CREDENTIAL_TYPES:
                    continue

                if schema_id in hashes:
                    continue

                data = {
                    "api_token": settings.API_TOKEN,
                    "did": did.did,
                    "hash": schema_id
                }
                requests.post(
                    settings.VERIFIABLE_REGISTER_URL + '/registerPair',
                    data=data
                )

    def get_verificable_register(self, did):
        response = requests.get(
            settings.VERIFIABLE_REGISTER_URL + '/readPairs',
            params={'did': did.did}
        )
        response.raise_for_status()

        return response.json()['hashes']
