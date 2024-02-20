import os
import csv
import json

from pathlib import Path
from utils import credtools
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.cache import cache
from decouple import config
from idhub.models import DID, Schemas
from oidc4vp.models import Organization
from promotion.models import Promotion


User = get_user_model()


class Command(BaseCommand):
    help = "Insert minimum datas for the project"

    def handle(self, *args, **kwargs):
        ADMIN_EMAIL = config('ADMIN_EMAIL', 'admin@example.org')
        ADMIN_PASSWORD = config('ADMIN_PASSWORD', '1234')
        KEY_DIDS = config('KEY_DIDS', '1234')
        cache.set("KEY_DIDS", KEY_DIDS, None)

        self.create_admin_users(ADMIN_EMAIL, ADMIN_PASSWORD)
        if settings.CREATE_TEST_USERS:
            for u in range(1, 6):
                user = 'user{}@example.org'.format(u)
                self.create_users(user, '1234')

        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        ORGANIZATION = os.path.join(BASE_DIR, settings.ORG_FILE)
        with open(ORGANIZATION, newline='\n') as csvfile:
            f = csv.reader(csvfile, delimiter=';', quotechar='"')
            for r in f:
                self.create_organizations(r[0].strip(), r[1].strip())
        if settings.SYNC_ORG_DEV == 'y':
            self.sync_credentials_organizations("pangea.org", "somconnexio.coop")
            self.sync_credentials_organizations("local 8000", "local 9000")
        self.create_schemas()

    def create_admin_users(self, email, password):
        su = User.objects.create_superuser(email=email, password=password)
        su.set_encrypted_sensitive_data()
        su.save()
        self.create_defaults_dids(su)


    def create_users(self, email, password):
        u = User.objects.create(email=email, password=password)
        u.set_password(password)
        u.set_encrypted_sensitive_data()
        u.save()
        self.create_defaults_dids(u)


    def create_organizations(self, name, url):
        Organization.objects.create(name=name, response_uri=url)

    def sync_credentials_organizations(self, test1, test2):
        org1 = Organization.objects.get(name=test1)
        org2 = Organization.objects.get(name=test2)
        org2.my_client_id = org1.client_id
        org2.my_client_secret = org1.client_secret
        org1.my_client_id = org2.client_id
        org1.my_client_secret = org2.client_secret
        org1.save()
        org2.save()

    def create_defaults_dids(self, u):
        did = DID(label="Default", user=u, type=DID.Types.WEB)
        did.set_did()
        did.save()

    def create_schemas(self):
        schemas_files = os.listdir(settings.SCHEMAS_DIR)
        schemas = [x for x  in schemas_files 
            if not Schemas.objects.filter(file_schema=x).exists()]
        for x in schemas_files:
            if Schemas.objects.filter(file_schema=x).exists():
                continue
            self._create_schemas(x)

    def _create_schemas(self, file_name):
        data = self.open_file(file_name)
        try:
            ldata = json.loads(data)
            assert credtools.validate_schema(ldata)
            dname = ldata.get('name')
            title = ldata.get('title')
            assert dname
            assert title
        except Exception:
            title = ''
            _name = ''

        _name = json.dumps(ldata.get('name', ''))
        _description = json.dumps(ldata.get('description', ''))

        Schemas.objects.create(
            file_schema=file_name,
            data=data,
            type=title,
            _name=_name,
            _description=_description
        )

    def open_file(self, file_name):
        data = ''
        filename = Path(settings.SCHEMAS_DIR).joinpath(file_name)
        with filename.open() as schema_file:
            data = schema_file.read()

        return data
