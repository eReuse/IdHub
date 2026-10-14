"""The public credential endpoint.

``public/credentials/<hash>/`` is the only view in the project that needs no
login: it is what the QR stamped on an eIDAS1 PDF points at, so whoever holds
the paper can check the credential behind it. The hash is set by ``issue()``,
which is why an unissued credential has no public url at all.

It answers json by default and the uploaded PDF template as html when there is
one, and the choice is made by comparing the Accept header for equality.
"""
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import NoReverseMatch, reverse

from idhub.models import VCTemplatePdf
from test_support import factories
from test_support.base import IdHubTestCase


SCHEMA_FILE = 'membership-card.json'
DOMAIN = 'https://testserver'

ROW = {
    'organisation': 'Test Org',
    'affiliatedSince': '2024-01-01',
    'typeOfPerson': 'natural',
    'firstName': 'Dummy',
    'email': 'normaluser@example.org',
}

TEMPLATE = b'<html><body><h1>{{ firstName }}</h1><img src="{{ qr }}"></body></html>'

_UNSET = object()


class PublicCredentialJsonViewTest(IdHubTestCase):
    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema(SCHEMA_FILE)
        self.credential = factories.make_credential(
            self.user, self.schema, factories.make_did(label='Issuer'), ROW
        )
        self.credential.issue(
            factories.make_did(label='Subject', user=self.user), DOMAIN
        )
        # issue() only mutates; persisting is left to the caller.
        self.credential.save()

    def url(self, hash=_UNSET):
        if hash is _UNSET:
            hash = self.credential.hash
        return reverse('idhub:public_credential_json', args=[hash])

    def attach_template(self, content=TEMPLATE):
        self.credential.template_pdf = VCTemplatePdf.objects.create(
            name='Membership card',
            data=SimpleUploadedFile('card.html', content),
        )
        self.credential.save()

    def test_an_anonymous_visitor_gets_the_signed_credential(self):
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(
            response.content.decode(), self.credential.get_data()
        )

    def test_the_body_is_the_signed_json_and_not_the_template(self):
        payload = json.loads(self.client.get(self.url()).content)

        self.assertIn('proof', payload)
        self.assertEqual(payload['credentialSubject']['firstName'], 'Dummy')

    def test_it_is_offered_as_a_download_called_credential_json(self):
        self.assertEqual(
            self.client.get(self.url())['Content-Disposition'],
            'attachment; filename=credential.json',
        )

    def test_an_unknown_hash_is_not_found(self):
        self.assertEqual(self.client.get(self.url('deadbeef')).status_code, 404)

    def test_an_unissued_credential_has_no_public_url_to_be_reached_by(self):
        # The hash is empty until issue() computes it, and the route needs a
        # non-empty segment, so the endpoint cannot even be addressed.
        unissued = factories.make_credential(
            self.user, self.schema, factories.make_did(label='Other'), ROW
        )
        self.assertEqual(unissued.hash, '')
        with self.assertRaises(NoReverseMatch):
            self.url(unissued.hash)

    def test_being_logged_in_as_someone_else_changes_nothing(self):
        # No ownership check: the whole point is that a third party can read
        # the credential behind a QR code.
        self.admin_login()
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_without_a_template_the_accept_header_is_irrelevant(self):
        for accept in ('text/html', 'application/json', '*/*'):
            with self.subTest(accept=accept):
                response = self.client.get(self.url(), headers={'Accept': accept})
                self.assertEqual(response['Content-Type'], 'application/json')

    def test_a_template_turns_the_endpoint_into_an_html_page(self):
        self.attach_template()
        response = self.client.get(self.url(), headers={'Accept': 'text/html'})

        self.assertEqual(response['Content-Type'], 'text/html')
        self.assertIn('<h1>Dummy</h1>', response.content.decode())

    def test_the_html_embeds_the_qr_of_this_very_url(self):
        self.attach_template()
        response = self.client.get(self.url(), headers={'Accept': 'text/html'})

        self.assertIn('src="iVBORw0KGgo', response.content.decode())

    def test_asking_for_json_explicitly_still_gets_the_json(self):
        self.attach_template()
        response = self.client.get(
            self.url(), headers={'Accept': 'application/json'}
        )

        self.assertEqual(response['Content-Type'], 'application/json')

    def test_the_accept_header_is_compared_for_equality_not_negotiated(self):
        # A real client sends a list, so an api client that asks for json among
        # other types is served the html page instead.
        self.attach_template()
        response = self.client.get(
            self.url(), headers={'Accept': 'application/json, text/plain, */*'}
        )

        self.assertEqual(response['Content-Type'], 'text/html')

    def test_a_template_that_renders_nothing_is_served_as_an_empty_page(self):
        self.attach_template(b'')
        response = self.client.get(self.url(), headers={'Accept': 'text/html'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
