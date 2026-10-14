"""Attaching an eIDAS1 certificate to the credentials being imported.

``ImportForm`` is the only place where a certificate and a credential meet.
The ``eidas1`` field is *conditional*: it only exists when there is a
certificate registered, which is why the rest of the suite never sees it.
"""
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from idhub.admin.forms import ImportForm
from idhub.models import VCTemplatePdf, VerificableCredential
from test_support import factories
from test_support.base import IdHubTestCase


SCHEMA_FILE = 'membership-card.json'
EXCEL_NAME = 'membership-card.xlsx'


def read_excel():
    path = Path(settings.BASE_DIR).joinpath(
        'examples', 'excel_examples', EXCEL_NAME
    )
    return path.read_bytes()


class ImportFormEidas1Test(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema(SCHEMA_FILE)
        self.issuer = factories.make_did(label='Issuer')

    def make_certificate(self, available=True):
        return factories.make_eidas1_did(available=available)

    def make_pdf_template(self):
        return VCTemplatePdf.objects.create(
            name='Membership card',
            data=SimpleUploadedFile('card.html', b'<html>{{ qr }}</html>'),
        )

    def make_form(self, **overrides):
        data = {'did': self.issuer.did, 'schema': self.schema.id}
        data.update(overrides)
        return ImportForm(data=data, files={
            'file_import': SimpleUploadedFile(EXCEL_NAME, read_excel())
        })

    def valid_form(self, **overrides):
        form = self.make_form(**overrides)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        return form

    def test_the_eidas1_field_does_not_exist_without_a_certificate(self):
        # This is the state the rest of the suite runs in, which is why the
        # eIDAS1 path has never been exercised by test_credentials.py.
        self.assertNotIn('eidas1', self.make_form().fields)

    def test_registering_a_certificate_makes_the_field_appear(self):
        self.make_certificate()
        self.assertIn('eidas1', self.make_form().fields)

    def test_the_first_choice_is_empty_so_eidas1_stays_optional(self):
        certificate = self.make_certificate()
        choices = self.make_form().fields['eidas1'].choices

        self.assertEqual(choices[0], ('', ''))
        self.assertEqual(choices[1:], [(certificate.did, certificate.label)])

    def test_an_unavailable_certificate_is_not_offered(self):
        self.make_certificate(available=False)
        self.assertNotIn('eidas1', self.make_form().fields)

    def test_the_two_did_fields_never_offer_the_same_row(self):
        # The invariant: a certificate can only be chosen as eidas1, and an
        # issuer DID only as did. Keeping them apart is the whole point.
        certificate = self.make_certificate()
        form = self.make_form()

        self.assertEqual(
            form.fields['did'].choices, [(self.issuer.did, self.issuer.label)]
        )
        self.assertNotIn(
            certificate.did, [value for value, _label in form.fields['did'].choices]
        )

    def test_choosing_a_certificate_stamps_it_on_every_credential(self):
        certificate = self.make_certificate()
        credentials = self.valid_form(eidas1=certificate.did).save()

        self.assertTrue(credentials)
        for credential in credentials:
            self.assertEqual(credential.eidas1_did, certificate)

    def test_leaving_the_certificate_blank_issues_the_eidas2_way(self):
        self.make_certificate()
        for credential in self.valid_form(eidas1='').save():
            self.assertIsNone(credential.eidas1_did)

    def test_the_pdf_template_field_is_conditional_too(self):
        self.assertNotIn('template_pdf', self.make_form().fields)

        template = self.make_pdf_template()
        form = self.make_form()
        self.assertEqual(form.fields['template_pdf'].choices[0], ('', ''))
        self.assertEqual(
            form.fields['template_pdf'].choices[1:],
            [(template.id, template.name)],
        )

    def test_the_pdf_template_is_stamped_on_every_credential(self):
        certificate = self.make_certificate()
        template = self.make_pdf_template()
        credentials = self.valid_form(
            eidas1=certificate.did, template_pdf=template.id
        ).save()

        for credential in credentials:
            self.assertEqual(credential.template_pdf, template)

    def test_reimporting_updates_the_certificate_of_an_enabled_credential(self):
        # create_credential reuses the ENABLED row instead of adding a second
        # one, so a second import can turn an eIDAS2 credential into an
        # eIDAS1 one before it is issued.
        self.valid_form().save()
        credential = VerificableCredential.objects.first()
        self.assertIsNone(credential.eidas1_did)

        certificate = self.make_certificate()
        before = VerificableCredential.objects.count()
        self.valid_form(eidas1=certificate.did).save()

        self.assertEqual(VerificableCredential.objects.count(), before)
        credential.refresh_from_db()
        self.assertEqual(credential.eidas1_did, certificate)

    def test_a_certificate_offered_as_the_issuer_is_rejected_by_a_crash(self):
        # The ChoiceField is what keeps the certificate out of the `did`
        # field; clean() then reads cleaned_data["did"] unconditionally, so a
        # crafted post that fails that validation raises instead of
        # reporting a form error.
        certificate = self.make_certificate()
        with self.assertRaises(KeyError):
            self.make_form(did=certificate.did).is_valid()

    def test_an_unknown_issuer_is_the_same_crash(self):
        with self.assertRaises(KeyError):
            self.make_form(did='did:key:z6MkNotRegistered').is_valid()
