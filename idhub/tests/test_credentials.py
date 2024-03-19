import os
import json

from pathlib import Path
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.urls import reverse
from django.conf import settings

from idhub_auth.models import User
from idhub.models import DID, Schemas, VerificableCredential
from oidc4vp.models import Organization



PILOTS = [
    "course-credential",
    "federation-membership",
    "membership-card",
    "financial-vulnerability",
    "e-operator-claim",
]

class KeyFirstTimeTest(TestCase):
    def setUp(self):
        cache.set("KEY_DIDS", '')
        self.user = User.objects.create_user(
            email='user1@example.org',
            password='testpass12',
        )
        self.admin_user = User.objects.create_superuser(
                email='adminuser@example.org',
                password='adminpass12')
        self.org = Organization.objects.create(name="testserver", main=True)

        settings.DOMAIN = self.org.name
        settings.ENABLE_EMAIL = False
        settings.LANGUAGE_CODE = 'en'

    def set_cache(self):
        cache.set("KEY_DIDS", '1234', None)

    def user_login(self):
        self.client.login(email='user1@example.org',
                          password='testpass12')
    def admin_login(self):
        self.client.login(email='adminuser@example.org',
                          password='adminpass12')

    def test_user_without_key(self):
        cache.set("KEY_DIDS", '')
        self.user_login()
        response = self.client.get(reverse('idhub:user_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:user_waiting'))

    def test_admin_without_key(self):
        cache.set("KEY_DIDS", '')
        self.admin_login()
        response = self.client.get(reverse('idhub:admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:encryption_key'))

    def test_admin_addfirst_key(self):
        self.admin_login()
        response = self.client.get(reverse('idhub:encryption_key'))
        self.assertEqual(response.status_code, 200)

        data = {
            "key": 1
        }
        response = self.client.post(reverse('idhub:encryption_key'), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:admin_dashboard'))
        cache.set("KEY_DIDS", '')

class CredentialsViewTest(TestCase):

    def setUp(self):
        cache.set("KEY_DIDS", '1234', None)
        self.user = User.objects.create_user(
            email='user1@example.org',
            password='testpass12',
        )
        self.user.accept_gdpr=True
        self.user.save()

        self.admin_user = User.objects.create_superuser(
                email='adminuser@example.org',
                password='adminpass12')
        self.admin_user.accept_gdpr=True
        self.admin_user.save()
        self.org = Organization.objects.create(name="testserver", main=True)

        settings.DOMAIN = self.org.name
        settings.ENABLE_EMAIL = False
        settings.LANGUAGE_CODE = 'en'

        self.admin_login()
        self.create_schemas()

    def user_login(self):
        self.client.login(email='user1@example.org',
                          password='testpass12')
    def admin_login(self):
        self.client.login(email='adminuser@example.org',
                          password='adminpass12')
        
    def create_did(self, label="Default", user=None):
        did = DID.objects.create(
            label="Default",
            type=DID.Types.KEY.value,
            user=user
        )
        did.set_did()
        did.save()
        return did

    def create_schemas(self):
        schemas_files = os.listdir(settings.SCHEMAS_DIR)
        for x in schemas_files:
            if Schemas.objects.filter(file_schema=x).exists():
                continue
            self._create_schemas(x)

        s = Schemas.objects
        for p in PILOTS:
            f = "{}.json".format(p)
            self.assertTrue(s.filter(file_schema = f).exists())

    def _create_schemas(self, file_name):
        data = self.open_file(file_name)
        ldata = json.loads(data)
        title = ldata.get('title')

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

    def test_admin_create_did_key(self):
        self.admin_login()
        url = reverse('idhub:admin_dids_new')
        data = {"label": "Default", "type": DID.Types.KEY.value}
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:admin_dids'))

        response = self.client.get(response.url)
        self.assertIn("DID created successfully", response.content.decode('utf-8'))

    def test_user_create_did_key(self):
        self.user_login()
        url = reverse('idhub:user_dids_new')
        data = {"label": "Default", "type": DID.Types.KEY.value}
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:user_dids'))

        response = self.client.get(response.url)
        self.assertIn("DID created successfully", response.content.decode('utf-8'))

    def _upload_data_membership(self, fileschema):
        did = self.create_did()
        schema = Schemas.objects.get(file_schema__contains=fileschema)
        url = reverse('idhub:admin_import_add')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        examples = 'examples/excel_examples/'
        name_file = '{}.xlsx'.format(fileschema)
        with Path(__file__).parent.parent.parent.joinpath(examples).joinpath(
                name_file
        ).open('rb') as _f:
                file_content = _f.read()
        
        uploaded_file = SimpleUploadedFile(name_file, file_content)
        data = {
            "did": did.did,
            "schema": schema.id,
            "file_import": uploaded_file
        }
        
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:admin_import'))
        response = self.client.get(response.url)
        self.assertIn("successfully", response.content.decode('utf-8'))

    def test_upload_data(self):
        self.admin_login()
        for p in PILOTS:
            self._upload_data_membership(p)

    def _user_require_credentail(self, fileschema):
        self.admin_login()
        self._upload_data_membership(fileschema)
        schema = Schemas.objects.get(file_schema__contains=fileschema)
        cred = VerificableCredential.objects.get(schema=schema)
        url = reverse('idhub:user_credentials_request')
        did = self.create_did(user=self.user)

        self.user_login()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = {
            "did": did.did,
            "credential": cred.id,
        }
        
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:user_credentials'))
        response = self.client.get(response.url)
        self.assertIn("successfully", response.content.decode('utf-8'))

    def test_user_require_credential(self):
        for p in PILOTS:
            self._user_require_credentail(p)

    def test_remove_file_data(self):
        p = PILOTS[0]
        self.admin_login()
        self._upload_data_membership(p)
        url = reverse('idhub:admin_import_del', args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:admin_import'))

