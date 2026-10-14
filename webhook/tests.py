import json

from uuid import uuid4
from django.urls import reverse

from webhook.models import Token
from test_support.base import IdHubTestCase


class WebhookTokenViewTest(IdHubTestCase):

    def setUp(self):
        super().setUp()
        self.admin_login()

    def get_credential(self):
        return {'@context': ['https://www.w3.org/2018/credentials/v1', 'https://idhub.pangea.org/context/base.jsonld', 'https://idhub.pangea.org/context/membership-card.jsonld'], 'type': ['VerifiableCredential', 'VerifiableAttestation', 'MembershipCard'], 'id': 'http://localhost/credentials/1', 'issuer': {'id': 'did:web:idhub.pangea.org:dids:z6Mko7ParpJZzBopW48DY8125Tcz9hMCaH7YzteWKnFcVzhu', 'name': 'Pangea'}, 'issuanceDate': '2024-06-11T14:41:12Z', 'issued': '2024-06-11T14:41:12Z', 'validFrom': '2024-06-11T14:41:12Z', 'name': [{'value': 'Membership Card', 'lang': 'en'}, {'value': 'Carnet de soci/a', 'lang': 'ca_ES'}, {'value': 'Carnet de socio/a', 'lang': 'es'}], 'description': [{'value': "The membership card specifies an individual's subscription or enrollment in specific services or benefits issued by an organization.", 'lang': 'en'}, {'value': "El carnet de soci especifica la subscripció o la inscripció d'un individu en serveis o beneficis específics emesos per una organització.", 'lang': 'ca_ES'}, {'value': 'El carnet de socio especifica la suscripción o inscripción de un individuo en servicios o beneficios específicos emitidos por uns organización.', 'lang': 'es'}], 'credentialSubject': {'id': 'did:web:localhost:did-registry:z6MkoAQJ96ppDQFw1idhvcR9NssPJQLFBoVDD2L62r7fh5yS', 'firstName': 'Pedro', 'lastName': 'Lagasta', 'email': 'user1@example.org', 'typeOfPerson': 'natural', 'organisation': 'Pangea', 'membershipType': 'Employee', 'membershipId': '1a', 'affiliatedSince': '2023-01-01'}, 'credentialSchema': {'id': 'https://idhub.pangea.org/vc_schemas/membership-card.json', 'type': 'FullJsonSchemaValidator2021'}, 'proof': {'type': 'Ed25519Signature2018', 'proofPurpose': 'assertionMethod', 'verificationMethod': 'did:web:idhub.pangea.org:dids:z6Mko7ParpJZzBopW48DY8125Tcz9hMCaH7YzteWKnFcVzhu#z6Mko7ParpJZzBopW48DY8125Tcz9hMCaH7YzteWKnFcVzhu', 'created': '2024-06-11T14:59:37Z', 'jws': 'eyJhbGciOiJFZERTQSIsImNyaXQiOlsiYjY0Il0sImI2NCI6ZmFsc2V9..kC2_QSkWRQ_fZ6C0_lRWvf4xuuxOueeCMb6dQFPKyn1h3gAHg_tb98RETIZeaQD6759wjJuH-IPJpvo4vzCDDA'}}

    def test_render_tokens_page(self):
        response = self.client.get('/webhook/tokens/', follow=True)

        self.assertEqual(response.status_code, 200)

    def test_new_token(self):
        response = self.client.get('/webhook/tokens/new', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.count(), 0)

        response = self.client.post(
            '/webhook/tokens/new',
            data={"label": "Test token"},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.count(), 1)

        tk = Token.objects.first()
        self.assertEqual(tk.label, "Test token")
        self.assertTrue(tk.token)
        self.assertTrue(tk.active)
        url = "/webhook/tokens/{}/del".format(tk.id)
        response = self.client.get(url, follow=True)

        self.assertEqual(Token.objects.count(), 0)

    def test_verify(self):
        token = uuid4()
        Token.objects.create(token=token)
        data = {
            "type": "credential",
            "data": self.get_credential()
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = self.client.post(
            reverse('webhook:verify'),
            content_type='application/json',
            data=data,
            headers=headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'success'})
        self.client.headers = None
