import os
import csv
import json

from pathlib import Path
from utils import credtools
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from pyvckit.did import (
    generate_did,
    gen_did_document,
)

from idhub.models import Schemas, DID
from oidc4vp.models import Organization
from webhook.models import Token


User = get_user_model()


class Command(BaseCommand):
    help = "Insert minimum data for the project"
    DOMAIN = settings.DOMAIN
    OIDC_ORGS = settings.OIDC_ORGS

    def add_arguments(self, parser):
        parser.add_argument('predefined_token', nargs='?', default='', type=str, help='predefined token')
        parser.add_argument('predefined_did', nargs='?', default='', type=str, help='predefined did')

    def handle(self, *args, **kwargs):
        ADMIN_EMAIL = settings.INITIAL_ADMIN_EMAIL
        ADMIN_PASSWORD = settings.INITIAL_ADMIN_PASSWORD
        self.predefined_token = kwargs['predefined_token']
        self.predefined_did = kwargs['predefined_did']
        cache.set("KEY_DIDS", "1", None)

        self.org = Organization.objects.create(
            name=self.DOMAIN,
            domain=self.DOMAIN,
            main=True
        )
        self.org.set_encrypted_sensitive_data()
        self.org.save()

        self.create_admin_users(ADMIN_EMAIL, ADMIN_PASSWORD)
        if settings.CREATE_TEST_USERS:
            for u in range(1, 6):
                user = 'user{}@example.org'.format(u)
                self.create_users(user, '1234')

        if self.OIDC_ORGS:
            self.create_organizations()

        self.create_schemas()

    def create_admin_users(self, email, password):
        su = User.objects.create_superuser(email=email, password=password)
        su.save()

        if self.predefined_token:
            tk = Token.objects.filter(token=self.predefined_token).first()
            if not tk:
                Token.objects.create(token=self.predefined_token)

        self.create_default_did()

    def create_default_did(self):

        fdid = self.open_example_did()
        if not fdid:
            return

        did = DID(type=DID.Types.WEB)
        new_key_material = fdid.get("key_material", "")
        label = fdid.get("label", "")
        if not new_key_material:
            return

        did.set_key_material(new_key_material)

        if label:
            did.label = label

        if did.type == did.Types.KEY:
            did.did = generate_did(new_key_material)
        elif did.type == did.Types.WEB:
            url = "https://{}".format(settings.DOMAIN)
            path = reverse("idhub:serve_did", args=["a"])

            if path:
                path = path.split("/a/did.json")[0]
                url = "https://{}/{}".format(settings.DOMAIN, path)

            did.did = generate_did(new_key_material, url)
            key = json.loads(new_key_material)
            url, did.didweb_document = gen_did_document(did.did, key)

        did.save()

    def open_example_did(self):
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        didweb_path = os.path.join(BASE_DIR, "examples", "keys_did.json")

        if self.predefined_did:
           didweb_path = self.predefined_did

        data = ''
        with open(didweb_path) as _file:
            try:
                data = json.loads(_file.read())
            except Exception:
                pass

        return data

    def create_users(self, email, password):
        u = User.objects.create(email=email, password=password)
        u.set_password(password)
        u.save()

    def create_organizations(self):
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        ORGANIZATION = os.path.join(BASE_DIR, self.OIDC_ORGS)
        DOMAIN = self.DOMAIN

        with open(ORGANIZATION, newline='\n') as csvfile:
            f = csv.reader(csvfile, delimiter=';', quotechar='"')
            exist_main_domain = False
            for r in f:
                if DOMAIN == r[2].strip():
                    exist_main_domain = True
                self.create_one_organization(r[0].strip(), r[1].strip(), r[2].strip())

            assert exist_main_domain, f"{DOMAIN} is not in {ORGANIZATION}"

        if settings.SYNC_ORG_DEV == 'y':
            self.sync_credentials_organizations("pangea.org", "somconnexio.coop")
            self.sync_credentials_organizations("local 8000", "local 9000")

    def create_one_organization(self, name, url, domain):
        if self.DOMAIN == domain:
            self.org.name = name
            self.org.response_uri = url
            self.org.save()
        else:
            Organization.objects.create(name=name, response_uri=url, domain=domain)

    def sync_credentials_organizations(self, test1, test2):
        org1 = Organization.objects.get(name=test1)
        org2 = Organization.objects.get(name=test2)
        org2.my_client_id = org1.client_id
        org2.my_client_secret = org1.client_secret
        org1.my_client_id = org2.client_id
        org1.my_client_secret = org2.client_secret
        org1.save()
        org2.save()

    def create_schemas(self):
        schemas_files = os.listdir(settings.SCHEMAS_DIR)
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
            ldata = {}
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
