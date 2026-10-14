"""The VerificableCredential model in isolation.

``test_credentials.py`` already drives the whole admin-uploads-excel to
user-gets-credential flow through the views; what it does not do is assert
anything about ``issue()``, ``render()`` or ``get_context()`` beyond the view
answering "successfully". That is what lives here.

Signing is real (it is fast once the @context loader is offline), so these
tests also cover that a credential built from a pilot schema validates
against it.
"""
import json

from unittest.mock import Mock, mock_open, patch

from nacl.exceptions import CryptoError

from django.test import override_settings

from idhub.models import DID, Schemas, VerificableCredential
from test_support import factories
from test_support.base import IdHubTestCase


SCHEMA_FILE = 'membership-card.json'
DOMAIN = 'https://testserver'

# The columns membership-card.json marks as required, minus 'id', which the
# template fills in from the subject DID.
ROW = {
    'organisation': 'Test Org',
    'affiliatedSince': '2024-01-01',
    'typeOfPerson': 'natural',
    'firstName': 'Dummy',
    'email': 'normaluser@example.org',
}

ETH_KEY_MATERIAL = {
    'kty': 'OKP',
    'crv': 'Ed25519',
    'eth_api_token': 't' * 80,
    'eth_subject_pub_key': 'subject-eth-key',
    'eth_issuer_pub_key': 'issuer-eth-key',
    'eth_chainid': 1337,
}


class CredentialTestCase(IdHubTestCase):
    def setUp(self):
        super().setUp()
        factories.make_schema(SCHEMA_FILE)
        self.schema = Schemas.objects.get(file_schema=SCHEMA_FILE)
        self.issuer_did = factories.make_did(label='issuer')
        self.subject_did = factories.make_did(label='subject', user=self.user)

    def make_credential(self, row=None, **kwargs):
        return factories.make_credential(
            self.user,
            self.schema,
            kwargs.pop('issuer_did', self.issuer_did),
            ROW if row is None else row,
            **kwargs,
        )

    def make_eidas1_did(self):
        return DID.objects.create(
            label='certificate', type=DID.Types.KEY, eidas1=True,
            did='signerDNIe004.pfx',
        )

    def make_webeth_did(self, user=None):
        did = DID(
            label='eth', type=DID.Types.WEBETH, user=user,
            did='did:web:testserver:abcdef',
        )
        did.set_key_material(json.dumps(ETH_KEY_MATERIAL))
        did.save()
        return did


class CredentialAccessorsTest(CredentialTestCase):
    def test_set_type_comes_from_the_schema_title(self):
        cred = self.make_credential()
        self.assertEqual(cred.type, 'MembershipCard')
        self.assertEqual(cred.get_type(), 'MembershipCard')
        self.assertEqual(self.schema.get_schema['title'], 'Membership Card')

    def test_get_status_is_the_label(self):
        cred = self.make_credential()
        self.assertEqual(cred.get_status(), 'Enabled')

        cred.status = VerificableCredential.Status.REVOKED
        self.assertEqual(cred.get_status(), 'Revoked')

    def test_get_issued_on_is_empty_until_issued(self):
        cred = self.make_credential()
        self.assertEqual(cred.get_issued_on(), '')

        cred.issue(self.subject_did, DOMAIN)
        self.assertEqual(
            cred.get_issued_on(), cred.issued_on.strftime('%m/%d/%Y')
        )

    def test_get_description_keeps_the_json_quoting(self):
        # _description is stored as json.dumps(...) by ImportSchemaForm, and
        # get_description() hands back the raw column. description() reads the
        # schema instead and gives the plain string. Same concept, two values.
        cred = self.make_credential()
        self.assertEqual(cred.get_description(), self.schema._description)
        self.assertEqual(json.loads(cred.get_description()), cred.description())

    def test_issuer_type_properties(self):
        expected = {
            DID.Types.KEY: (False, False),
            DID.Types.WEB: (True, False),
            DID.Types.WEBETH: (False, True),
        }
        for type, (is_didweb, is_webeth) in expected.items():
            with self.subTest(type=type.label):
                self.issuer_did.type = type.value
                cred = self.make_credential()
                self.assertEqual(cred.is_didweb, is_didweb)
                self.assertEqual(cred.is_webeth, is_webeth)

    def test_data_is_encrypted_for_its_own_user(self):
        cred = self.make_credential()
        self.assertEqual(cred.get_data(), '')

        cred.set_data('{"a": 1}')
        self.assertNotIn('"a"', cred.data)
        self.assertEqual(cred.get_data(), '{"a": 1}')

        cred.user = factories.make_user('other@example.org', 'pass12345')
        with self.assertRaises(CryptoError):
            cred.get_data()


class FilterDictTest(CredentialTestCase):
    def test_drops_zero_and_false_along_with_the_empty_values(self):
        # This is why a credentialSubject field whose value is 0 or False
        # silently disappears from the issued credential: filter_dict keeps
        # whatever is truthy, not whatever is present.
        cred = self.make_credential()
        self.assertEqual(
            cred.filter_dict({
                'zero': 0, 'false': False, 'empty': '', 'none': None,
                'list': [], 'kept': 'yes',
            }),
            {'kept': 'yes'},
        )

    def test_drops_dicts_that_end_up_empty(self):
        cred = self.make_credential()
        self.assertEqual(
            cred.filter_dict({'outer': {'inner': ''}, 'kept': {'inner': 'yes'}}),
            {'kept': {'inner': 'yes'}},
        )


class GetContextTest(CredentialTestCase):
    def test_points_at_the_private_credential_url(self):
        cred = self.make_credential()
        context = cred.get_context(DOMAIN)

        self.assertEqual(context['vc_id'], '{}/credentials/{}'.format(DOMAIN, cred.id))
        self.assertEqual(context['id_credential'], str(cred.id))
        self.assertEqual(context['issuer_did'], self.issuer_did.did)
        self.assertEqual(context['organisation'], 'Test Org')
        self.assertEqual(context['type'], 'MembershipCard')

    def test_is_empty_where_the_credential_is_not_issued_yet(self):
        context = self.make_credential().get_context(DOMAIN)
        self.assertEqual(context['subject_did'], '')
        self.assertEqual(context['issuance_date'], '')

    def test_eidas1_makes_the_url_public_and_keyed_by_hash(self):
        # The semantic difference of eIDAS1: the credential becomes publicly
        # resolvable by hash instead of by its primary key.
        cred = self.make_credential(eidas1_did=self.make_eidas1_did())
        cred.hash = 'abc123'

        context = cred.get_context(DOMAIN)
        self.assertEqual(
            context['vc_id'], '{}/public/credentials/abc123'.format(DOMAIN)
        )
        self.assertEqual(context['id_credential'], 'abc123')

    def test_credential_status_is_only_a_real_did_for_didweb(self):
        cred = self.make_credential()
        self.assertEqual(
            cred.get_context(DOMAIN)['credential_status_id'],
            'https://revocation.not.supported/',
        )

        self.issuer_did.type = DID.Types.WEB.value
        self.assertEqual(
            cred.get_context(DOMAIN)['credential_status_id'], self.issuer_did.did
        )

    def test_csv_data_overrides_the_user_fields(self):
        # context.update(d) runs last, so a spreadsheet column wins over the
        # name and email held in the User row.
        row = dict(ROW, firstName='From Excel', email='excel@example.org')
        context = self.make_credential(row=row).get_context(DOMAIN)

        self.assertEqual(context['firstName'], 'From Excel')
        self.assertEqual(context['email'], 'excel@example.org')
        self.assertNotEqual(self.user.email, context['email'])

    def test_ether_dids_contribute_their_own_keys(self):
        cred = self.make_credential(issuer_did=self.make_webeth_did())
        cred.subject_did = self.make_webeth_did(user=self.user)

        context = cred.get_context(DOMAIN)
        self.assertEqual(context['issuer_id'], 'issuer-eth-key')
        self.assertEqual(context['subject_did'], 'subject-eth-key')


class RenderTest(CredentialTestCase):
    def render(self, cred, domain=DOMAIN):
        return json.loads(cred.render(domain))

    def test_empty_fields_are_dropped(self):
        document = self.render(self.make_credential())

        self.assertNotIn('id', document['credentialSubject'])
        self.assertNotIn('issuanceDate', document)
        self.assertNotIn('validFrom', document)

    def test_the_subject_id_appears_once_issued(self):
        cred = self.make_credential()
        cred.issue(self.subject_did, DOMAIN)

        document = self.render(cred)
        self.assertEqual(document['credentialSubject']['id'], self.subject_did.did)
        self.assertEqual(document['validFrom'], document['issuanceDate'])

    def test_the_local_context_is_appended(self):
        document = self.render(self.make_credential())
        self.assertEqual(
            document['@context'][-1], '{}/context/base.jsonld'.format(DOMAIN)
        )

    def test_a_schema_context_replaces_the_local_one(self):
        self.schema.context = 'https://example.org/context/custom.jsonld'
        self.schema.save()

        document = self.render(self.make_credential())
        self.assertEqual(document['@context'][-1], self.schema.context)

    def test_credential_schema_points_at_the_schema_id(self):
        document = self.render(self.make_credential())
        self.assertEqual(document['credentialSchema']['id'], self.schema.url)
        self.assertTrue(self.schema.url.endswith(SCHEMA_FILE))

    def test_only_columns_declared_in_the_schema_are_copied(self):
        row = dict(ROW, notInTheSchema='dropped')
        document = self.render(self.make_credential(row=row))

        self.assertIn('organisation', document['credentialSubject'])
        self.assertNotIn('notInTheSchema', document['credentialSubject'])

    def test_evidence_is_copied_verbatim(self):
        row = dict(ROW, evidence=[{'type': 'DocumentVerification'}])
        document = self.render(self.make_credential(row=row))

        self.assertEqual(document['evidence'], [{'type': 'DocumentVerification'}])

    def test_credential_status_survives_only_for_didweb(self):
        self.assertNotIn('credentialStatus', self.render(self.make_credential()))

        self.issuer_did.type = DID.Types.WEB.value
        self.assertIn('credentialStatus', self.render(self.make_credential()))


class IssueTest(CredentialTestCase):
    def test_issue_signs_and_stores_the_credential(self):
        cred = self.make_credential()
        cred.issue(self.subject_did, DOMAIN)

        self.assertEqual(cred.status, VerificableCredential.Status.ISSUED)
        self.assertEqual(cred.subject_did, self.subject_did)
        self.assertIsNotNone(cred.issued_on)

        signed = json.loads(cred.get_data())
        self.assertIn('proof', signed)
        self.assertEqual(signed['issuer']['id'], self.issuer_did.did)

    def test_the_hash_covers_the_unsigned_credential(self):
        import hashlib

        cred = self.make_credential()
        cred.issue(self.subject_did, DOMAIN)

        self.assertEqual(
            cred.hash,
            hashlib.sha3_256(cred.render(DOMAIN).encode()).hexdigest(),
        )

    def test_save_false_returns_the_signature_but_still_mutates(self):
        # save=False only skips writing `data` and `status`; subject_did,
        # issued_on and hash are already set by then. The name suggests a
        # dry run, and it is not one.
        cred = self.make_credential()
        signed = cred.issue(self.subject_did, DOMAIN, save=False)

        self.assertIn('proof', json.loads(signed))
        self.assertEqual(cred.status, VerificableCredential.Status.ENABLED)
        self.assertEqual(cred.data, '')
        self.assertEqual(cred.subject_did, self.subject_did)
        self.assertIsNotNone(cred.issued_on)
        self.assertTrue(cred.hash)

    def test_issuing_twice_is_a_silent_no_op(self):
        cred = self.make_credential()
        cred.issue(self.subject_did, DOMAIN)
        issued_on, data = cred.issued_on, cred.data

        other_did = factories.make_did(label='other', user=self.user)
        self.assertIsNone(cred.issue(other_did, DOMAIN))

        self.assertEqual(cred.issued_on, issued_on)
        self.assertEqual(cred.data, data)
        self.assertEqual(cred.subject_did, self.subject_did)

    def test_a_row_that_breaks_the_schema_fails_after_mutating(self):
        cred = self.make_credential(row={'organisation': 'Test Org'})

        with self.assertRaises(Exception):
            cred.issue(self.subject_did, DOMAIN)

        # Half-issued: not ISSUED and without data, but already stamped.
        self.assertEqual(cred.status, VerificableCredential.Status.ENABLED)
        self.assertEqual(cred.data, '')
        self.assertIsNotNone(cred.issued_on)
        self.assertEqual(cred.subject_did, self.subject_did)

    def test_get_datas_reads_the_rendered_subject(self):
        cred = self.make_credential()
        cred.issue(self.subject_did, DOMAIN)

        datas = dict(cred.get_datas())
        self.assertEqual(datas['id'], self.subject_did.did)
        self.assertEqual(datas['organisation'], 'Test Org')


@override_settings(API_DLT_URL='http://dlt.example.org')
class CallOracleTest(CredentialTestCase):
    def issued_credential(self, subject_did):
        cred = self.make_credential(issuer_did=self.make_webeth_did())
        cred.subject_did = subject_did
        cred.set_data(json.dumps({'credential': 'signed'}))
        cred.save()
        return cred

    def run_oracle(self, cred, status='Success'):
        response = Mock(json=Mock(return_value={'Status': status}))
        with patch.dict('os.environ', {'ADMIN_TOKEN_FILE': 'admin.token'}), \
             patch('builtins.open', mock_open(read_data='admin-token\n')), \
             patch('idhub.models.requests.post', return_value=response) as post:
            return cred.call_oracle(), post

    def test_mints_and_allows_tokens_for_an_ether_subject(self):
        cred = self.issued_credential(self.make_webeth_did(user=self.user))
        result, post = self.run_oracle(cred)

        self.assertTrue(result)
        urls = [call.args[0] for call in post.call_args_list]
        self.assertEqual(urls, [
            'http://dlt.example.org/oracle',
            'http://dlt.example.org/mintTokens',
            'http://dlt.example.org/allowTokens',
        ])
        self.assertEqual(
            post.call_args_list[1].kwargs['json']['Address'], 'subject-eth-key'
        )
        self.assertEqual(
            post.call_args_list[2].kwargs['json']['api_token'], 't' * 80
        )

    def test_reports_a_failed_status(self):
        cred = self.issued_credential(self.make_webeth_did(user=self.user))
        result, _ = self.run_oracle(cred, status='Error')
        self.assertFalse(result)

    def test_a_subject_without_ether_keys_blows_up_on_an_unbound_name(self):
        # operator_address is only assigned inside the `if did is WEBETH`
        # branch, so any other subject reaches mintTokens with the name
        # undefined. The oracle call has already gone out by then.
        cred = self.issued_credential(self.subject_did)

        with self.assertRaises(UnboundLocalError):
            self.run_oracle(cred)
