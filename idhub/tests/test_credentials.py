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

class AdminDashboardViewTest(TestCase):

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

        self.admin_login()
        self.create_schemas()

    def user_login(self):
        self.client.login(email='user1@example.org',
                          password='testpass12')
    def admin_login(self):
        self.client.login(email='adminuser@example.org',
                          password='adminpass12')
        
    def create_did(self, label="Default"):
        did = DID.objects.create(label=label, type=DID.Types.WEB.value)
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
            assert s.filter(file_schema = f).exists()

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

    def test_create_did_web(self):
        url = reverse('idhub:admin_dids_new')
        data = {"label": "Default", "type": DID.Types.WEB.value}
        response = self.client.get(url)
        assert response.status_code == 200
        response = self.client.post(url, data=data)
        assert response.status_code == 302
        assert response.url == reverse('idhub:admin_dids')
        response = self.client.get(response.url)
        assert "DID created successfully" in response.content.decode('utf-8')

    def _upload_data_membership(self, fileschema):
        did = self.create_did()
        schema = Schemas.objects.get(file_schema__contains=fileschema)
        url = reverse('idhub:admin_import_add')
        
        response = self.client.get(url)
        assert response.status_code == 200
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

        assert response.status_code == 302
        assert response.url == reverse('idhub:admin_import')
        response = self.client.get(response.url)
        assert "successfully" in response.content.decode('utf-8')

    def test_upload_data(self):
        for p in PILOTS:
            self._upload_data_membership(p)

    def test_user_require_credentail(self):
        p = PILOTS[0]
        self._upload_data_membership(p)
        schema = Schemas.objects.get(file_schema__contains=p)
        cred = VerificableCredential.objects.get(schema=schema)
        url = reverse('idhub:user_credentials_request')
        did = DID.objects.create(
            label="Default",
            type=DID.Types.WEB.value,
            user=self.user
        )

        self.user_login()
        response = self.client.get(url)
        assert response.status_code == 200

        data = {
            "did": did.did,
            "credential": cred.id,
        }
        
        response = self.client.post(url, data=data)
        import pdb; pdb.set_trace()

        assert response.status_code == 302
        assert response.url == reverse('idhub:user_credentials')
        response = self.client.get(response.url)
        assert "successfully" in response.content.decode('utf-8')
