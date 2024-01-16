import os
import csv
import json

from pathlib import Path
from utils import credtools
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
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
        USER_EMAIL = config('USER_EMAIL', 'user1@example.org')
        USER_PASSWORD = config('USER_PASSWORD', '1234')

        self.create_admin_users(ADMIN_EMAIL, ADMIN_PASSWORD)
        self.create_users(USER_EMAIL, USER_PASSWORD)

        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        ORGANIZATION = os.path.join(BASE_DIR, 'examples/organizations.csv')
        with open(ORGANIZATION, newline='\n') as csvfile:
            f = csv.reader(csvfile, delimiter=';', quotechar='"')
            for r in f:
                self.create_organizations(r[0].strip(), r[1].strip())
        self.sync_credentials_organizations("pangea.org", "somconnexio.coop")
        self.sync_credentials_organizations("local 8000", "local 9000")
        self.create_defaults_dids()
        self.create_schemas()

    def create_admin_users(self, email, password):
        User.objects.create_superuser(email=email, password=password)


    def create_users(self, email, password):
        u= User.objects.create(email=email, password=password)
        u.set_password(password)
        u.save()


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

    def create_defaults_dids(self):
        for u in User.objects.all():
            did = DID(label="Default", user=u, type=DID.Types.KEY)
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
            assert dname
        except Exception:
            return
        name = ''
        try:
            for x in dname:
                if settings.LANGUAGE_CODE in x['lang']:
                    name = x.get('value', '')
        except Exception:
            return

        Schemas.objects.create(file_schema=file_name, data=data, type=name)

    def open_file(self, file_name):
        data = ''
        filename = Path(settings.SCHEMAS_DIR).joinpath(file_name)
        with filename.open() as schema_file:
            data = schema_file.read()

        return data
