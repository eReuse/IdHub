"""The endpoints anybody can GET: DID documents, schemas and ``@context``.

None of them is authenticated, and that is the point: these URLs are what an
external verifier dereferences while checking a credential this instance
issued. A 404 or a malformed body here makes every credential of the
deployment unverifiable, so each of these four-line views gets tested.
"""
import base64
import json
import zlib

import pyroaring

from unittest.mock import patch

from django.urls import reverse

from idhub.models import Context, ContextFile, DID, VerificableCredential
from test_support import factories
from test_support.base import IdHubTestCase


def revocation_service(response):
    """Reads the service entry back the way a verifier would."""
    service, = json.loads(response.content)['service']
    return service


def revoked_indexes(response):
    endpoint = revocation_service(response)['serviceEndpoint']
    encoded = endpoint.split('base64,')[1]
    bitmap = zlib.decompress(base64.b64decode(encoded))
    return set(pyroaring.BitMap.deserialize(bitmap))


class ServeDidTest(IdHubTestCase):
    """``/.well-known/<id>/did.json``: the DID document plus its revocations."""

    def setUp(self):
        super().setUp()
        self.did = factories.make_did(label='Web', type=DID.Types.WEB)
        self.url = self.did.get_path()

    def revoke(self, credential):
        credential.status = VerificableCredential.Status.REVOKED
        credential.save()

    def make_credential(self):
        schema = factories.make_schema('membership-card.json')
        return factories.make_credential(self.user, schema, self.did)

    def test_the_document_is_served_as_json_without_logging_in(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content)['id'], self.did.did)

    def test_the_stored_document_is_served_untouched_except_for_the_service(self):
        credential = self.make_credential()
        self.revoke(credential)

        response = self.client.get(self.url)

        served = json.loads(response.content)
        stored = json.loads(self.did.didweb_document)
        self.assertEqual(
            {k: v for k, v in served.items() if k != 'service'},
            {k: v for k, v in stored.items() if k != 'service'},
        )
        # pyvckit already wrote a RevocationBitmap2022 into the document when
        # the DID was created, and it is empty forever: the list is only right
        # when it is this view that builds it.
        self.assertEqual(revoked_indexes(response), {credential.id})
        self.assertNotEqual(served['service'], stored['service'])

    def test_a_did_nobody_has_registered_is_a_404(self):
        self.assertEqual(self.client.get(reverse(
            'idhub:serve_did', args=['nothing-here']
        )).status_code, 404)

    def test_the_service_entry_is_a_revocation_bitmap(self):
        service = revocation_service(self.client.get(self.url))

        self.assertEqual(service['id'], self.did.did + '#revocation')
        self.assertEqual(service['type'], 'RevocationBitmap2022')

    def test_the_revocation_service_is_published_even_with_nothing_revoked(self):
        # There is a TODO in the view about adding it conditionally. Until that
        # happens every DID advertises a revocation list, which is harmless but
        # means an empty bitmap is the normal answer, not a sign of trouble.
        self.assertEqual(revoked_indexes(self.client.get(self.url)), set())

    def test_a_revoked_credential_is_listed_and_a_live_one_is_not(self):
        revoked = self.make_credential()
        self.make_credential()
        self.revoke(revoked)

        self.assertEqual(revoked_indexes(self.client.get(self.url)), {revoked.id})

    def test_the_index_the_commented_out_line_wants_does_not_exist(self):
        # Both views carry `revoked_credential_indexes.append(
        # credential.revocationBitmapIndex)` commented out, next to a TODO. The
        # field was never added to the model, so uncommenting it is an
        # AttributeError: the primary key is not a stopgap, it is the only
        # index there is.
        credential = self.make_credential()

        self.assertFalse(hasattr(credential, 'revocationBitmapIndex'))


class ServeDidRegistryTest(IdHubTestCase):
    """``/did-registry/<id>/did.json``: the same code, a different prefix."""

    DID_ID = 'abc123'

    def make_registry_did(self):
        did_string = 'did:web:testserver:did-registry:' + self.DID_ID
        did = DID(
            label='Registry',
            type=DID.Types.WEB,
            did=did_string,
            didweb_document=json.dumps({'id': did_string}),
        )
        did.set_key_material('{}')
        did.save()
        return did

    def test_a_registry_did_is_served_with_its_revocation_service(self):
        self.make_registry_did()

        response = self.client.get(
            reverse('idhub:serve_registry_did', args=[self.DID_ID])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(revocation_service(response)['type'], 'RevocationBitmap2022')

    def test_the_duplicated_code_builds_the_same_revocation_list(self):
        did = self.make_registry_did()
        schema = factories.make_schema('membership-card.json')
        credential = factories.make_credential(self.user, schema, did)
        credential.status = VerificableCredential.Status.REVOKED
        credential.save()

        response = self.client.get(
            reverse('idhub:serve_registry_did', args=[self.DID_ID])
        )

        self.assertEqual(revoked_indexes(response), {credential.id})

    def test_a_registry_did_nobody_registered_is_a_404(self):
        response = self.client.get(
            reverse('idhub:serve_registry_did', args=['nothing-here'])
        )

        self.assertEqual(response.status_code, 404)

    def test_no_did_this_instance_creates_can_ever_reach_this_route(self):
        # set_did() only moves the base url out of /.well-known/ when the
        # serve_did route does not contain it, and it does. So the whole view
        # is unreachable with the current urls: thirty lines duplicated from
        # ServeDidView for a prefix nothing produces.
        did = factories.make_did(label='Web', type=DID.Types.WEB)

        self.assertNotIn(':did-registry:', did.did)
        self.assertIn('.well-known', did.get_path())


class SchemaTest(IdHubTestCase):
    """``/schema/<file_name>``: what ``credentialSchema`` points at."""

    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema('membership-card.json')

    def test_the_schema_is_served_verbatim_without_logging_in(self):
        response = self.client.get(
            reverse('idhub:schema', args=[self.schema.file_schema])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), json.loads(self.schema.data))

    def test_a_schema_that_is_not_loaded_is_a_404(self):
        response = self.client.get(reverse('idhub:schema', args=['nothing.json']))

        self.assertEqual(response.status_code, 404)


class ContextTest(IdHubTestCase):
    """``/context/base.jsonld``: the JSON-LD vocabulary of every credential."""

    def test_every_term_of_the_database_is_published(self):
        Context.objects.create(key='affiliatedSince')
        Context.objects.create(key='typeOfPerson')

        response = self.client.get(reverse('idhub:context'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(
            set(json.loads(response.content)['@context']),
            {'affiliatedSince', 'typeOfPerson'},
        )

    def test_an_instance_with_no_terms_still_answers_a_valid_context(self):
        response = self.client.get(reverse('idhub:context'))

        self.assertEqual(json.loads(response.content), {'@context': {}})

    def test_the_terms_resolve_against_pangea_and_not_this_deployment(self):
        # Context.get_context() defaults its domain to idhub.pangea.org, and
        # the view calls it without one: any other deployment publishes a
        # vocabulary whose terms point at somebody else's host.
        Context.objects.create(key='affiliatedSince')

        terms = json.loads(self.client.get(reverse('idhub:context')).content)

        self.assertEqual(
            terms['@context']['affiliatedSince'],
            'https://idhub.pangea.org/context/#affiliatedSince',
        )


class ContextFileTest(IdHubTestCase):
    """``/context/<file_name>``: the uploaded contexts of imported schemas."""

    def test_the_file_is_served_as_json_without_logging_in(self):
        ContextFile.objects.create(
            file_name='custom.jsonld',
            data='{"a": 1}',
            schema=factories.make_schema('membership-card.json'),
        )

        response = self.client.get(
            reverse('idhub:context_file', args=['custom.jsonld'])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(json.loads(response.content), {'a': 1})

    def test_a_file_nobody_uploaded_is_a_404(self):
        response = self.client.get(
            reverse('idhub:context_file', args=['custom.jsonld'])
        )

        self.assertEqual(response.status_code, 404)


class AvailableDidTest(IdHubTestCase):
    """``/available/<did>/``: is our own did:web reachable from outside?"""

    def url(self, did):
        return reverse('idhub:available_did', args=[did.did])

    def make_web_did(self, user=None, available=True):
        did = factories.make_did(label='Web', type=DID.Types.WEB, user=user)
        if not available:
            did.available = False
            did.save()
        return did

    def test_without_a_session_there_is_nothing_to_look_at(self):
        did = self.make_web_did()

        response = self.client.get(self.url(did))

        self.assertEqual(response.status_code, 302)

    def test_a_did_already_known_to_be_up_is_a_redirect_to_its_document(self):
        self.user_login()
        did = self.make_web_did(user=self.user)

        response = self.client.get(self.url(did))

        self.assertRedirects(response, did.get_path())

    def test_a_did_that_answers_from_outside_is_marked_as_available(self):
        self.user_login()
        did = self.make_web_did(user=self.user, available=False)

        with patch.object(DID, 'check_remote_did', return_value=True):
            response = self.client.get(self.url(did))

        did.refresh_from_db()
        self.assertTrue(did.available)
        self.assertRedirects(response, did.get_path())

    def test_a_did_the_outside_cannot_see_is_handed_over_as_a_download(self):
        # The fallback of a deployment that is not published yet: the admin
        # downloads did.json and uploads it to the web server by hand.
        self.user_login()
        did = self.make_web_did(user=self.user, available=False)

        with patch.object(DID, 'check_remote_did', return_value=False):
            response = self.client.get(self.url(did))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(
            response.headers['Content-Disposition'],
            'attachment; filename=did.json',
        )
        self.assertEqual(response.content.decode(), did.didweb_document)
        did.refresh_from_db()
        self.assertFalse(did.available)

    def test_a_did_key_has_no_document_to_publish(self):
        self.user_login()
        did = factories.make_did(label='Key', user=self.user)

        self.assertEqual(self.client.get(self.url(did)).status_code, 404)

    def test_somebody_elses_did_is_a_404(self):
        self.user_login()
        did = self.make_web_did(user=self.admin_user)

        self.assertEqual(self.client.get(self.url(did)).status_code, 404)

    def test_an_admin_also_gets_the_dids_of_the_organization(self):
        self.admin_login()
        did = self.make_web_did()

        self.assertRedirects(
            self.client.get(self.url(did)), did.get_path(),
            fetch_redirect_response=False,
        )

    def test_an_admin_does_not_get_the_dids_of_other_people(self):
        self.admin_login()
        did = self.make_web_did(user=self.user)

        self.assertEqual(self.client.get(self.url(did)).status_code, 404)
