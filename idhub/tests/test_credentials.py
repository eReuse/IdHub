import json

from pathlib import Path
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings

from idhub.models import DID, Schemas, VerificableCredential
from test_support import factories
from test_support.base import IdHubTestCase


PILOTS = [
    "course-credential",
    "federation-membership",
    "membership-card",
    "financial-vulnerability",
    "ereuse-role",
]

class KeyFirstTimeTest(IdHubTestCase):
    USER_EMAIL = 'user1@example.org'
    KEY_DIDS = ''

    def test_user_without_key(self):
        self.user_login()
        response = self.client.get(reverse('idhub:user_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('idhub:user_waiting'))

    def test_admin_without_key(self):
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


class CredentialsViewTest(IdHubTestCase):
    USER_EMAIL = 'user1@example.org'

    def setUp(self):
        super().setUp()
        self.admin_login()
        self.create_schemas()

    def create_did(self, label="Default", user=None):
        return factories.make_did(label=label, user=user)

    def create_schemas(self):
        factories.make_schemas()
        for p in PILOTS:
            f = "{}.json".format(p)
            self.assertTrue(Schemas.objects.filter(file_schema=f).exists())

    def open_file(self, file_name):
        return Path(settings.SCHEMAS_DIR).joinpath(file_name).read_text()

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
        schema = Schemas.objects.get(file_schema='{}.json'.format(fileschema))
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
        schema = Schemas.objects.get(file_schema='{}.json'.format(fileschema))
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

