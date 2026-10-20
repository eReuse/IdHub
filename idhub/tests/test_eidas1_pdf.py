"""Signing the credential PDF with the eIDAS1 certificate.

``CredentialPdfView`` renders the credential to a PDF and, when the credential
carries an ``eidas1_did``, signs that PDF with the certificate stored in the
DID row. This is the only place where the certificate is actually used.

Rendering with weasyprint costs about a second, so only ``PdfRenderTest``
renders the real template; everywhere else ``build_certificate`` is replaced by
a one-paragraph PDF, which also makes the template a test parameter.
"""
import base64
import json

from io import BytesIO
from unittest.mock import patch

import weasyprint

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.urls import reverse
from pyhanko.pdf_utils.reader import PdfFileReader

from idhub.models import VCTemplatePdf
from idhub.user.views import CredentialPdfView
from test_support import factories
from test_support.base import IdHubTestCase


SCHEMA_FILE = 'membership-card.json'
CERT_COMMON_NAME = 'Ficticio Activo, Ciudadano (FIRMA)'

_rendered = None


def one_paragraph_pdf():
    """A real but minimal PDF, rendered once for the whole module."""
    global _rendered
    if _rendered is None:
        _rendered = weasyprint.HTML(string='<p>credential</p>').write_pdf()
    return _rendered


def build_from(template):
    """A build_certificate that renders nothing and pins self.template_pdf.

    insert_signature branches on the template, so replacing build_certificate
    means the replacement has to leave it behind just like the original.
    """
    def build_certificate(self):
        self.template_pdf = template
        return one_paragraph_pdf()
    return build_certificate


class Eidas1PdfTestCase(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema(SCHEMA_FILE)
        self.credential = factories.make_credential(
            self.user,
            self.schema,
            factories.make_did(label='Issuer'),
            csv_data={'firstName': 'Ciudadano', 'lastName': 'Ficticio'},
        )

    def url(self, credential=None):
        return reverse(
            'idhub:user_credential_pdf', args=[(credential or self.credential).id]
        )

    def attach_certificate(self, **kwargs):
        certificate = factories.make_eidas1_did(**kwargs)
        self.credential.eidas1_did = certificate
        self.credential.save()
        return certificate


class PfxDataTest(Eidas1PdfTestCase):
    """get_pfx_data and signer_init, without going through the view."""

    def view(self):
        view = CredentialPdfView()
        view.object = self.credential
        return view

    def test_a_credential_without_a_certificate_has_no_bundle(self):
        self.assertEqual(self.view().get_pfx_data(), (None, None))

    def test_the_bundle_is_decoded_and_the_passphrase_encoded(self):
        self.attach_certificate()
        pfx_data, passphrase = self.view().get_pfx_data()

        self.assertEqual(pfx_data, factories.read_eidas1_pfx())
        self.assertEqual(passphrase, factories.EIDAS1_PFX_PASSWORD.encode())

    def test_a_bundle_missing_a_key_is_reported_as_no_bundle_at_all(self):
        for material in ({}, {'cert': 'x'}, {'passphrase': 'x'}):
            with self.subTest(material=material):
                self.attach_certificate(material=material)
                self.assertEqual(self.view().get_pfx_data(), (None, None))

    def test_signer_init_reads_the_certificate_of_the_bundle(self):
        self.attach_certificate()
        signer = self.view().signer_init()

        self.assertIn(
            CERT_COMMON_NAME, signer.signing_cert.subject.human_friendly
        )

    def test_signer_init_returns_none_when_the_bundle_cannot_be_opened(self):
        # load_cert swallows the error and returns None, so a corrupt bundle is
        # indistinguishable here from one that was never stored.
        self.attach_certificate(material={
            'cert': base64.b64encode(b'not a bundle').decode(),
            'passphrase': factories.EIDAS1_PFX_PASSWORD,
        })
        self.assertIsNone(self.view().signer_init())

    def test_a_wrong_passphrase_is_the_same_none(self):
        self.attach_certificate(material={
            'cert': base64.b64encode(factories.read_eidas1_pfx()).decode(),
            'passphrase': 'not the password',
        })
        self.assertIsNone(self.view().signer_init())


class PdfSignatureTest(Eidas1PdfTestCase):
    """What comes out of the view, with the rendering stubbed out."""

    TEMPLATE_WITH_QR = '<p>{{ qr }}</p>'
    TEMPLATE_WITHOUT_QR = '<p>no qr anywhere</p>'

    def download(self, template=TEMPLATE_WITH_QR):
        self.user_login()
        with patch.object(
            CredentialPdfView, 'build_certificate', build_from(template)
        ):
            return self.client.get(self.url())

    def signatures(self, pdf):
        return PdfFileReader(BytesIO(pdf)).embedded_signatures

    def test_a_credential_without_a_certificate_is_served_unsigned(self):
        response = self.download()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response.content, one_paragraph_pdf())

    def test_the_attachment_is_always_called_certificate_pdf(self):
        self.assertEqual(
            self.download()['Content-Disposition'],
            'attachment; filename=certificate.pdf',
        )

    def test_the_signature_is_embedded_and_readable(self):
        self.attach_certificate()
        pdf = self.download().content

        self.assertTrue(pdf.startswith(b'%PDF'))
        signature, = self.signatures(pdf)
        self.assertEqual(signature.field_name, 'Signature')
        self.assertIn(
            CERT_COMMON_NAME, signature.signer_cert.subject.human_friendly
        )

    def test_signing_appends_to_the_rendered_pdf_instead_of_replacing_it(self):
        # sign_pdf writes an incremental update, and the view reads the buffer
        # back without seeking: a regression there would serve an empty body.
        self.attach_certificate()
        pdf = self.download().content

        self.assertGreater(len(pdf), len(one_paragraph_pdf()))
        self.assertTrue(pdf.startswith(one_paragraph_pdf()))

    def test_a_template_without_a_qr_gets_a_visible_signature_field(self):
        # The qr already carries the url, so the stamp is only added when the
        # template has no placeholder for it.
        self.attach_certificate()
        with_qr = self.download(self.TEMPLATE_WITH_QR).content
        without_qr = self.download(self.TEMPLATE_WITHOUT_QR).content

        self.assertGreater(len(without_qr), len(with_qr))
        for pdf in (with_qr, without_qr):
            self.assertEqual(len(self.signatures(pdf)), 1)

    def test_a_certificate_that_cannot_be_opened_serves_the_word_none(self):
        # insert_signature returns None when signer_init fails, get() passes
        # that straight to HttpResponse, and nothing in between notices: the
        # user downloads a certificate.pdf holding four bytes of text.
        self.attach_certificate(material={})
        response = self.download()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response.content, b'None')


class PdfAccessTest(Eidas1PdfTestCase):
    def test_an_anonymous_visitor_is_sent_to_the_login_page(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('idhub:login'), response['Location'])

    def test_the_credential_of_another_user_is_not_found(self):
        other = factories.make_user('other@example.org', 'otherpass12')
        self.credential.user = other
        self.credential.save()
        self.user_login()

        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_without_the_encryption_key_the_download_is_abandoned(self):
        # Silently, and the dashboard it aims at bounces the user on to the
        # waiting page, so nothing ever explains why the download did nothing.
        self.set_key_dids(None)
        self.user_login()
        response = self.client.get(self.url(), follow=True)

        self.assertEqual(response.redirect_chain, [
            (reverse('idhub:user_dashboard'), 302),
            (reverse('idhub:user_waiting'), 302),
        ])
        self.assertFalse(list(response.context['messages']))

    def test_a_rendering_error_becomes_a_message_on_the_credential_page(self):
        self.user_login()
        with patch.object(
            CredentialPdfView, 'build_certificate', side_effect=ValueError
        ):
            response = self.client.get(self.url(), follow=True)

        self.assertEqual(response.redirect_chain, [(
            reverse('idhub:user_credential', args=[self.credential.id]), 302
        )])
        self.assertEqual(
            [str(message) for message in response.context['messages']],
            ['Error rendering this credencial'],
        )

    def test_a_failure_to_sign_is_reported_as_a_rendering_error_too(self):
        # The try block covers both steps, so the message blames the rendering
        # whatever went wrong.
        self.attach_certificate()
        self.user_login()
        with patch.object(
            CredentialPdfView, 'insert_signature', side_effect=ValueError
        ):
            response = self.client.get(self.url(), follow=True)

        self.assertEqual(
            [str(message) for message in response.context['messages']],
            ['Error rendering this credencial'],
        )


class PdfRenderTest(Eidas1PdfTestCase):
    """build_certificate and the context: the only real template renders."""

    URL_ID = 'https://testserver/public/credentials/abc123'

    def view(self):
        view = CredentialPdfView()
        view.object = self.credential
        view.request = RequestFactory().get('/')
        view.request.user = self.user
        view.url_id = self.URL_ID
        view.kwargs = {}
        return view

    def test_the_shipped_template_renders_a_pdf(self):
        self.assertTrue(self.view().build_certificate().startswith(b'%PDF'))

    def test_an_uploaded_template_is_preferred_over_the_shipped_one(self):
        self.credential.template_pdf = VCTemplatePdf.objects.create(
            name='card',
            data=SimpleUploadedFile('card.html', b'<p>{{ firstName }}</p>'),
        )
        self.credential.save()
        view = self.view()
        view.build_certificate()

        self.assertEqual(view.template_pdf, '<p>{{ firstName }}</p>')

    def test_the_template_name_is_never_actually_per_schema(self):
        # get() formats template_name with the schema file name, but the
        # string has no placeholder, so every credential without an uploaded
        # template renders the same certificates/base.html.
        self.assertEqual(
            CredentialPdfView.template_name.format('membership-card'),
            'certificates/base.html',
        )

    def test_the_context_carries_the_excel_data_and_the_qr(self):
        self.credential.csv_data = json.dumps({
            'firstName': 'Ciudadano', 'membershipType': 'FULL',
        })
        context = self.view().get_context_data()

        self.assertEqual(context['firstName'], 'Ciudadano')
        self.assertEqual(context['membership_type'], 'full')
        self.assertTrue(context['qr'])

    def test_the_qr_is_a_png_derived_from_the_url(self):
        view = self.view()
        qr = base64.b64decode(view.generate_qr_code(self.URL_ID))

        self.assertTrue(qr.startswith(b'\x89PNG'))
        self.assertEqual(qr, base64.b64decode(view.generate_qr_code(self.URL_ID)))
        self.assertNotEqual(
            qr, base64.b64decode(view.generate_qr_code(self.URL_ID + '0'))
        )
