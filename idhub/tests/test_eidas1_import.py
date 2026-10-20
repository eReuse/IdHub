"""Registering an eIDAS1 certificate.

eIDAS1 is the classic electronic signature: an X.509 certificate in a PKCS#12
bundle signs the *PDF*, not the JSON-LD credential. It is stored as a DID row
with ``eidas1=True`` whose ``key_material`` holds the bundle, so this is where
a certificate enters the system.

The fixture is the generic DNIe test certificate already in ``examples/``.
"""
import base64
import json

from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from idhub.admin.forms import ImportCertificateForm
from idhub.models import DID, Event
from test_support import factories
from test_support.base import IdHubTestCase


def upload(content=None, name=None):
    return SimpleUploadedFile(
        name or factories.EIDAS1_PFX_NAME,
        content if content is not None else factories.read_eidas1_pfx(),
    )


class ImportCertificateFormTest(IdHubTestCase):
    LABEL = 'DNIe of the organisation'

    def make_form(self, label=None, password=None, file=None, with_file=True):
        files = {'file_import': file or upload()} if with_file else {}
        data = {'label': label if label is not None else self.LABEL}
        if password is not None:
            data['password'] = password
        return ImportCertificateForm(data=data, files=files)

    def valid_form(self):
        form = self.make_form(password=factories.EIDAS1_PFX_PASSWORD)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        return form

    def test_a_valid_certificate_builds_an_eidas1_did(self):
        did = self.valid_form().save()

        self.assertTrue(did.eidas1)
        self.assertEqual(did.get_type(), DID.Types.KEY)
        self.assertEqual(did.label, self.LABEL)
        self.assertIsNone(did.user)
        self.assertEqual(DID.objects.count(), 1)

    def test_the_did_field_holds_the_file_name(self):
        # Not a DID at all: this row is a certificate container, and the
        # column is reused to remember which file it came from.
        self.assertEqual(self.valid_form().save().did, factories.EIDAS1_PFX_NAME)

    def test_the_bundle_survives_the_round_trip_byte_for_byte(self):
        material = json.loads(self.valid_form().save().get_key_material())

        self.assertEqual(sorted(material), ['cert', 'passphrase'])
        self.assertEqual(
            base64.b64decode(material['cert']), factories.read_eidas1_pfx()
        )
        self.assertEqual(material['passphrase'], factories.EIDAS1_PFX_PASSWORD)

    def test_the_passphrase_is_encrypted_at_rest(self):
        # It is stored in the clear inside key_material, so the only thing
        # protecting it is the KEY_DIDS encryption of the whole column.
        did = self.valid_form().save()
        self.assertNotIn(factories.EIDAS1_PFX_PASSWORD, did.key_material)
        self.assertNotIn('passphrase', did.key_material)

    def test_save_without_commit_persists_nothing(self):
        # And returns None, which is what the view's error branch keys on.
        self.assertIsNone(self.valid_form().save(commit=False))
        self.assertFalse(DID.objects.exists())

    def test_a_wrong_password_is_a_form_error(self):
        form = self.make_form(password='not the password')
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['__all__'], ['Is not a valid certificate']
        )
        self.assertFalse(DID.objects.exists())

    def test_a_file_that_is_not_a_pkcs12_bundle_is_a_form_error(self):
        form = self.make_form(
            password=factories.EIDAS1_PFX_PASSWORD, file=upload(b'not a bundle')
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['__all__'], ['Is not a valid certificate']
        )

    def test_a_missing_password_is_a_form_error(self):
        form = self.make_form()
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

    def test_a_missing_file_is_a_crash(self):
        # clean() calls file_import.read() before checking anything, and
        # cleaned_data has no 'file_import' key when the field failed its own
        # validation, so the form raises instead of reporting the error.
        with self.assertRaises(AttributeError):
            self.make_form(
                password=factories.EIDAS1_PFX_PASSWORD, with_file=False
            ).is_valid()

    def test_an_empty_file_is_the_same_crash(self):
        # FileField rejects an empty upload, so `if not self.pfx_file` is
        # never the branch that catches it.
        with self.assertRaises(AttributeError):
            self.make_form(
                password=factories.EIDAS1_PFX_PASSWORD, file=upload(b'')
            ).is_valid()

    def test_nothing_stops_the_same_certificate_being_registered_twice(self):
        # DIDForm.clean() rejects a duplicate label and a duplicate did; this
        # form checks neither, so two rows end up indistinguishable.
        for _attempt in range(2):
            form = self.make_form(
                label='same', password=factories.EIDAS1_PFX_PASSWORD
            )
            self.assertTrue(form.is_valid(), form.errors.as_text())
            form.save()

        self.assertEqual(DID.objects.count(), 2)
        self.assertEqual(
            set(DID.objects.values_list('did', 'label')),
            {(factories.EIDAS1_PFX_NAME, 'same')},
        )

    def test_without_the_encryption_key_the_form_raises(self):
        # set_key_material cannot derive a key, so validation blows up. The
        # GET of the view redirects to the encryption-key page, but the POST
        # has no such guard (see the view test below).
        self.set_key_dids(None)
        with self.assertRaises(AttributeError):
            self.make_form(password=factories.EIDAS1_PFX_PASSWORD).is_valid()


class WalletConfigEidas1sViewTest(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse('idhub:admin_wallet_config_eidas1')

    def post(self, password=None, file=None):
        return self.client.post(self.url, data={
            'label': 'DNIe',
            'password': password or factories.EIDAS1_PFX_PASSWORD,
            'file_import': file or upload(),
        }, follow=True)

    def test_the_form_page_renders_for_an_admin(self):
        self.admin_login()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'idhub/admin/wallet_eidas1.html')

    def test_a_successful_upload_lands_on_the_identities_list(self):
        self.admin_login()
        response = self.post()

        self.assertEqual(
            response.redirect_chain, [(reverse('idhub:admin_dids'), 302)]
        )
        self.assertTrue(DID.objects.get().eidas1)
        self.assertEqual(
            [str(message) for message in response.context['messages']],
            ['The eIDAS1 identity was created successfully!'],
        )

    def test_a_successful_upload_is_logged_as_an_organisational_did(self):
        self.admin_login()
        self.post()

        self.assertEqual(
            Event.objects.get().type, Event.Types.EV_ORG_DID_CREATED_BY_ADMIN
        )

    def test_a_rejected_certificate_redisplays_the_form(self):
        self.admin_login()
        response = self.post(password='not the password')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [])
        self.assertEqual(
            response.context['form'].errors['__all__'],
            ['Is not a valid certificate'],
        )
        self.assertFalse(DID.objects.exists())

    def test_the_error_branch_of_form_valid_is_unreachable(self):
        # form_valid always calls save() with the default commit=True, and
        # that never returns None, so "Error creating eIDAS1 identity!" can
        # only be produced by patching the form.
        self.admin_login()
        with patch.object(ImportCertificateForm, 'save', return_value=None):
            response = self.post()

        self.assertEqual(
            [str(message) for message in response.context['messages']],
            ['Error creating eIDAS1 identity!'],
        )

    def test_a_plain_user_is_sent_to_their_dashboard(self):
        self.user_login()
        response = self.post()

        self.assertEqual(
            response.redirect_chain, [(reverse('idhub:user_dashboard'), 302)]
        )
        self.assertFalse(DID.objects.exists())

    def test_the_get_redirects_when_the_encryption_key_is_missing(self):
        self.admin_login()
        self.set_key_dids(None)
        response = self.client.get(self.url, follow=True)

        self.assertEqual(
            response.redirect_chain, [(reverse('idhub:encryption_key'), 302)]
        )

    def test_the_post_has_no_such_guard_and_returns_a_server_error(self):
        # UserView.post reads KEY_DIDS into self.admin_validated but, unlike
        # UserView.get, never acts on it: it calls super().post() first, so
        # the form runs and raises. An admin whose session lost the key gets a
        # 500 instead of being sent to the encryption-key page.
        self.admin_login()
        self.set_key_dids(None)
        # assertLogs also keeps the 500 traceback out of the test output.
        with self.assertLogs('django.request', 'ERROR'):
            with self.assertRaises(AttributeError):
                self.post()
