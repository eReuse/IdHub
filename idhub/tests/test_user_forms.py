"""What the holder's own forms do, and where they stop short.

``idhub/user/forms.py`` was only ever exercised sideways, through the five
views that build it, so the half the views never reach was untested. That
half is where the module is most surprising: four of its five ``save()``
methods can return ``None`` for several unrelated reasons -- a row that does
not belong to the caller, a peer that answered something other than 200, a
signature that did not verify -- and the caller gets the same ``None`` for
all of them.

Where the current behaviour looks wrong the test pins it as it is and the
reason is recorded in ``bugs_encontrados.org``, so that fixing the code
turns the test red on purpose.
"""
import json

from unittest.mock import patch

import requests

from django.test import override_settings

from idhub.models import DID, VerificableCredential
from idhub.user.forms import (
    DIDForm,
    DemandAuthorizationForm,
    ProfileForm,
    RequestCredentialForm,
    TermsConditionsForm,
)
from oidc4vp.models import Organization
from test_support import factories
from test_support.base import IdHubTestCase


SCHEMA_FILE = 'membership-card.json'

# did:web needs a dotted domain to pass sanitize_didweb, which 'testserver'
# is not.
WEB_DOMAIN = 'idhub.example.org'


def errors(form):
    return form.errors.get('__all__', [])


class ProfileFormTest(IdHubTestCase):
    """The holder's profile form, which nothing imports.

    ``ProfileView`` builds its own form out of ``fields``, and the admin
    side uses the homonymous form in ``idhub_auth.forms``. This one is
    reachable only from a test.
    """

    def test_the_mandatory_fields_it_declares_are_not_mandatory(self):
        # MANDATORY_FIELDS is read by nobody: not by clean(), not by a
        # template. Only email, which the model declares non-blank, is
        # really required.
        form = ProfileForm(data={'email': 'someone@example.org'})

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(ProfileForm.MANDATORY_FIELDS[:2], ['first_name', 'last_name'])

    def test_an_email_already_taken_is_refused(self):
        form = ProfileForm(data={'email': self.USER_EMAIL})

        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


@override_settings(
    POLICY_PRIVACY='https://example.org/privacy',
    POLICY_LEGAL='https://example.org/legal',
    POLICY_COOKIES='https://example.org/cookies',
)
class TermsConditionsFormTest(IdHubTestCase):
    """Accepting the GDPR terms.

    The three checkboxes are ``required=False``, so the form never refuses
    anything: it records the answer on the user and lets the view through
    either way. Deciding what to do about a refusal is left to the view.
    """

    def form(self, **data):
        return TermsConditionsForm(data=data, user=self.user)

    def accepted(self):
        return {
            'accept_privacy': 'on',
            'accept_legal': 'on',
            'accept_cookies': 'on',
        }

    def test_accepting_the_three_policies_grants_consent(self):
        form = self.form(**self.accepted())

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertIs(form.save(), self.user)
        self.user.refresh_from_db()
        self.assertTrue(self.user.accept_gdpr)

    def test_leaving_one_policy_unchecked_withholds_consent(self):
        for left_out in ('accept_privacy', 'accept_legal', 'accept_cookies'):
            with self.subTest(left_out=left_out):
                data = self.accepted()
                del data[left_out]
                form = self.form(**data)

                self.assertTrue(form.is_valid(), form.errors.as_text())
                self.assertFalse(form.save().accept_gdpr)

    def test_an_empty_submission_is_accepted_and_withdraws_consent(self):
        # The user arrives here with accept_gdpr already true (the view only
        # shows the page to revisit it), and an empty POST takes it away.
        self.assertTrue(self.user.accept_gdpr)
        form = self.form()

        self.assertTrue(form.is_valid(), form.errors.as_text())
        form.save()

        self.user.refresh_from_db()
        self.assertFalse(self.user.accept_gdpr)

    def test_consent_is_decided_in_clean_and_only_written_by_save(self):
        self.user.accept_gdpr = False
        self.user.save()
        form = self.form(**self.accepted())
        form.is_valid()

        # clean() mutates the user object it was handed, so the decision is
        # visible before save() and lost if save() never runs.
        self.assertTrue(form.user.accept_gdpr)
        self.assertIsNone(form.save(commit=False))
        self.user.refresh_from_db()
        self.assertFalse(self.user.accept_gdpr)

    def test_without_a_user_the_form_crashes_instead_of_refusing(self):
        # user= defaults to None, and clean() writes on it unconditionally.
        form = TermsConditionsForm(data=self.accepted())

        with self.assertRaises(AttributeError):
            form.is_valid()

    def test_each_label_links_to_the_policy_url_in_the_settings(self):
        form = self.form()
        labels = {
            form.privacy_label(): 'https://example.org/privacy',
            form.legal_label(): 'https://example.org/legal',
            form.cookies_label(): 'https://example.org/cookies',
        }

        for label, url in labels.items():
            with self.subTest(url=url):
                self.assertIn('href="{}"'.format(url), label)
                self.assertIn('target="_blank"', label)
                self.assertIn('I read and accepted the', label)

    def test_the_label_names_the_policy_it_points_at(self):
        form = self.form()

        self.assertIn('>Privacy policy<', form.privacy_label())
        self.assertIn('>Legal policy<', form.legal_label())
        self.assertIn('>Cookies policy<', form.cookies_label())


class RequestCredentialFormTest(IdHubTestCase):
    """Asking for one of your enabled credentials to be signed.

    ``save()`` is the only place in the project where a credential is issued
    on the holder's behalf, and it reads ``self.data`` directly instead of
    ``cleaned_data``, so the choices the field validated are not the values
    it uses.
    """

    DOMAIN = 'https://testserver'

    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema(SCHEMA_FILE)
        self.issuer_did = factories.make_did(label='Issuer')
        self.subject_did = factories.make_did(label='Subject', user=self.user)
        self.cred = factories.make_credential(
            self.user, self.schema, self.issuer_did, factories.MEMBERSHIP_ROW
        )

    def form(self, did=None, credential=None, domain=DOMAIN, user=None, **kwargs):
        data = {
            'did': self.subject_did.did if did is None else did,
            'credential': str(self.cred.id) if credential is None else credential,
        }
        return RequestCredentialForm(
            data=data,
            user=self.user if user is None else user,
            domain=domain,
            **kwargs
        )

    def test_the_choices_only_offer_your_own_available_dids(self):
        hidden = factories.make_did(label='Not available', user=self.user)
        hidden.available = False
        hidden.save()
        other = factories.make_user('other@example.org', 'testpass12')
        factories.make_did(label='Theirs', user=other)

        offered = dict(self.form().fields['did'].choices)

        self.assertEqual(list(offered), [self.subject_did.did])

    def test_the_choices_only_offer_your_own_enabled_credentials(self):
        issued = factories.make_credential(
            self.user, self.schema, self.issuer_did,
            status=VerificableCredential.Status.ISSUED,
        )
        other = factories.make_user('other@example.org', 'testpass12')
        factories.make_credential(other, self.schema, self.issuer_did)

        offered = dict(self.form().fields['credential'].choices)

        self.assertEqual(list(offered), [self.cred.id])
        self.assertNotIn(issued.id, offered)

    def test_a_credential_is_signed_and_becomes_issued(self):
        form = self.form()

        self.assertTrue(form.is_valid(), form.errors.as_text())
        cred = form.save()

        self.assertEqual(cred.id, self.cred.id)
        self.cred.refresh_from_db()
        self.assertEqual(self.cred.status, VerificableCredential.Status.ISSUED)
        self.assertEqual(self.cred.subject_did, self.subject_did)
        self.assertTrue(self.cred.data)

    def test_asking_twice_finds_nothing_the_second_time(self):
        # The lookup in save() is restricted to ENABLED, so the "already
        # issued" shortcut inside issue() is unreachable from here: a second
        # request is indistinguishable from a credential that is not yours.
        self.form().save()
        form = self.form()
        form.is_valid()

        self.assertIsNone(form.save())
        self.assertEqual(errors(form), [])

    def test_a_did_that_belongs_to_someone_else_issues_nothing(self):
        other = factories.make_user('other@example.org', 'testpass12')
        theirs = factories.make_did(label='Theirs', user=other)
        form = self.form(did=theirs.did)
        form.is_valid()

        self.assertIsNone(form.save())
        self.cred.refresh_from_db()
        self.assertEqual(self.cred.status, VerificableCredential.Status.ENABLED)
        # Nothing is said about why, so the view reports the generic
        # "Error sending credential!" of form_invalid.
        self.assertEqual(errors(form), [])

    def test_a_credential_that_belongs_to_someone_else_issues_nothing(self):
        other = factories.make_user('other@example.org', 'testpass12')
        theirs = factories.make_credential(other, self.schema, self.issuer_did)
        form = self.form(credential=str(theirs.id))
        form.is_valid()

        self.assertIsNone(form.save())
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, VerificableCredential.Status.ENABLED)

    def test_a_credential_that_is_no_longer_enabled_issues_nothing(self):
        self.cred.status = VerificableCredential.Status.REVOKED
        self.cred.save()
        form = self.form()
        form.is_valid()

        self.assertIsNone(form.save())

    def test_a_failed_issuance_is_reported_as_a_non_field_error(self):
        form = self.form()
        form.is_valid()

        with patch.object(
            VerificableCredential, 'issue', return_value=(False, 'the reason')
        ):
            self.assertIsNone(form.save())

        self.assertEqual(errors(form), ['the reason'])

    def test_without_commit_nothing_is_signed(self):
        form = self.form()
        form.is_valid()

        self.assertIsNone(form.save(commit=False))
        self.cred.refresh_from_db()
        self.assertEqual(self.cred.status, VerificableCredential.Status.ENABLED)

    def test_without_a_domain_nothing_is_signed_and_nothing_is_said(self):
        # The view always passes one, so this is the shape of the bug it
        # would hide: the same silent None as a row that is not yours.
        form = self.form(domain=None)
        form.is_valid()

        self.assertIsNone(form.save())
        self.cred.refresh_from_db()
        self.assertEqual(self.cred.status, VerificableCredential.Status.ENABLED)

    def test_save_reads_the_raw_data_so_a_missing_field_crashes(self):
        form = RequestCredentialForm(data={}, user=self.user, domain=self.DOMAIN)
        self.assertFalse(form.is_valid())

        with self.assertRaises(KeyError):
            form.save()

    def test_the_credential_label_is_asked_for_in_the_given_language(self):
        with patch.object(
            VerificableCredential, 'get_type', return_value='Etiqueta'
        ) as get_type:
            RequestCredentialForm(data={}, user=self.user, lang='es')

        get_type.assert_called_once_with(lang='es')


class DemandAuthorizationFormTest(IdHubTestCase):
    """Asking a peer instance to start a verification.

    ``save()`` returns the url the peer answered with, and ``None`` for
    everything else: an organization that does not exist, a reply that is
    not a 200, a 200 without a ``redirect_uri``.
    """

    def setUp(self):
        super().setUp()
        # make_organization leaves domain unset, and the form excludes by
        # domain, not by main.
        self.org.domain = 'testserver'
        self.org.save()
        self.verifier = Organization.objects.create(
            name='Verifier',
            domain='verifier.example.org',
            response_uri='https://verifier.example.org/oidc4vp/',
            my_client_id='my-client-id',
            my_client_secret='my-client-secret',
        )

    def form(self, organization=None, **kwargs):
        return DemandAuthorizationForm(
            data={
                'organization': (
                    str(self.verifier.id) if organization is None else organization
                ),
            },
            user=self.user,
            **kwargs
        )

    def reply(self, status_code=200, payload=None):
        response = requests.Response()
        response.status_code = status_code
        response._content = json.dumps(payload or {}).encode()
        return patch('oidc4vp.models.requests.get', return_value=response)

    def test_our_own_organization_is_not_offered_as_a_verifier(self):
        offered = dict(self.form().fields['organization'].choices)

        self.assertEqual(offered, {self.verifier.id: 'Verifier'})

    def test_an_organization_without_a_domain_is_offered_as_a_verifier(self):
        # The exclusion is by domain, so a row created without one -- which
        # is what the model defaults to -- is offered even when it is us.
        self.org.domain = None
        self.org.save()

        offered = dict(self.form().fields['organization'].choices)

        self.assertIn(self.org.id, offered)

    def test_the_redirect_url_the_verifier_answered_is_handed_back(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors.as_text())

        with self.reply(payload={'redirect_uri': 'https://verifier.example.org/go'}):
            self.assertEqual(form.save(), 'https://verifier.example.org/go')

        self.assertEqual(form.org, self.verifier)

    def test_a_reply_that_is_not_a_200_is_swallowed(self):
        form = self.form()
        form.is_valid()

        with self.reply(status_code=401):
            self.assertIsNone(form.save())

        self.assertEqual(errors(form), [])

    def test_a_200_without_a_redirect_url_is_swallowed(self):
        form = self.form()
        form.is_valid()

        with self.reply(payload={}):
            self.assertIsNone(form.save())

    def test_an_organization_that_does_not_exist_asks_nobody(self):
        form = self.form(organization='0')
        self.assertFalse(form.is_valid())

        with self.reply() as get:
            self.assertIsNone(form.save())

        get.assert_not_called()

    def test_after_an_unknown_organization_form_org_is_still_a_queryset(self):
        # DemandAuthorizationView's error handler reads form.org.response_uri
        # to name the peer it could not reach. Here there is no peer, and
        # the attribute belongs to a QuerySet.
        form = self.form(organization='0')
        form.save()

        self.assertFalse(hasattr(form.org, 'response_uri'))

    def test_without_commit_the_verifier_is_resolved_but_not_called(self):
        form = self.form()
        form.is_valid()

        with self.reply() as get:
            self.assertIsNone(form.save(commit=False))

        get.assert_not_called()
        self.assertEqual(form.org, self.verifier)

    def test_a_transport_error_is_left_for_the_view_to_report(self):
        form = self.form()
        form.is_valid()

        with patch(
            'oidc4vp.models.requests.get',
            side_effect=requests.ConnectionError('refused'),
        ):
            with self.assertRaises(requests.ConnectionError):
                form.save()


@override_settings(DOMAIN=WEB_DOMAIN)
class UserDIDFormTest(IdHubTestCase):
    """Registering an identity of your own.

    Like its admin twin the form cannot generate key material on its own:
    ``DidRegisterView`` builds a ``DID(user=..., type=WEB)``, calls
    ``set_did()`` on it, keeps it pickled in the session and the form edits
    *that*. Every test here hands it the same half-built instance.

    The two differences from the admin version are the ones worth pinning:
    the label must be unique per user rather than among the organisation's
    own dids, and the whole did is lowercased, path included.
    """

    def pregenerated(self, user=None):
        instance = DID(user=self.user if user is None else user, type=DID.Types.WEB)
        instance.set_did()
        return instance

    def form(self, instance=None, user=None, **data):
        if instance is None:
            instance = self.pregenerated(user=user)
        return DIDForm(
            instance=instance, data=data, user=self.user if user is None else user
        )

    def web_did(self, domain=WEB_DOMAIN, path='abc123'):
        return 'did:web:{}:{}'.format(domain, path)

    def test_a_did_on_our_own_domain_is_available(self):
        form = self.form(label='Ours', type=DID.Types.WEB, did=self.web_did())

        self.assertTrue(form.is_valid(), form.errors.as_text())
        did = form.save()
        self.assertEqual(did.did, self.web_did())
        self.assertEqual(did.user, self.user)
        self.assertTrue(did.available)
        self.assertTrue(did.didweb_document)

    def test_a_did_hosted_somewhere_else_is_saved_as_unavailable(self):
        form = self.form(
            label='Theirs',
            type=DID.Types.WEB,
            did='did:web:other.example.org:dids:abc123',
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertFalse(form.save().available)

    def test_the_whole_did_is_lowercased_path_included(self):
        # The admin form only lowercases the domain, which sanitize_didweb
        # does by itself; this one lowercases the did before handing it over,
        # so two paths that differ only in case become the same did.
        form = self.form(
            label='Mixed',
            type=DID.Types.WEB,
            did='did:web:{}:AbC123'.format(WEB_DOMAIN.upper()),
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.save().did, self.web_did(path='abc123'))

    def test_a_key_did_is_generated_and_the_typed_did_is_ignored(self):
        form = self.form(label='Key', type=DID.Types.KEY, did='did:web:nonsense')

        self.assertTrue(form.is_valid(), form.errors.as_text())
        did = form.save()
        self.assertTrue(did.did.startswith('did:key:'))
        self.assertEqual(did.user, self.user)
        self.assertTrue(did.available)
        self.assertFalse(did.didweb_document)

    def test_a_key_did_is_built_on_a_fresh_instance(self):
        # clean() replaces self.instance for the non-web types, so the key
        # material the view pre-generated is thrown away and generated again.
        instance = self.pregenerated()
        form = self.form(instance=instance, label='Key', type=DID.Types.KEY)
        form.is_valid()

        self.assertIsNot(form.instance, instance)

    def test_a_web_did_keeps_the_pre_generated_key_material(self):
        instance = self.pregenerated()
        generated = instance.did
        form = self.form(
            instance=instance, label='Ours', type=DID.Types.WEB, did=self.web_did()
        )
        form.is_valid()

        self.assertIs(form.instance, instance)
        self.assertEqual(form.instance.key_material, instance.key_material)
        self.assertNotEqual(form.save().did, generated)

    def test_submitting_the_did_unchanged_leaves_the_document_alone(self):
        # The did field is rendered pre-filled with what the view generated,
        # so submitting the page untouched lands here: clean() finds nothing
        # to recompute and the availability check is skipped with it.
        instance = self.pregenerated()
        instance.did = self.web_did()
        instance.get_did_document()
        document = instance.didweb_document
        form = self.form(
            instance=instance, label='Ours', type=DID.Types.WEB, did=self.web_did()
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        did = form.save()
        self.assertEqual(did.didweb_document, document)
        self.assertTrue(did.available)

    def test_a_webeth_did_never_reaches_the_distributed_ledger(self):
        # save() only calls set_did() when the did is not a web one, and
        # WEBETH is. So the ethereum account registration that lives inside
        # set_did() is skipped and the did keeps the plain web key material
        # the view pre-generated. Were it called, API_DLT_URL would be asked
        # for /registerUser and the offline mock would say so.
        instance = self.pregenerated()
        material = instance.key_material
        form = self.form(
            instance=instance, label='Ether', type=DID.Types.WEBETH,
            did=self.web_did(path='ether1'),
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        did = form.save()
        self.assertEqual(did.key_material, material)
        self.assertNotIn('eth_api_token', did.get_key_material())

    def test_a_web_did_without_a_did_is_refused(self):
        form = self.form(label='Ours', type=DID.Types.WEB)

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This field is required'])

    def test_something_that_is_not_a_did_web_is_refused(self):
        form = self.form(label='Ours', type=DID.Types.WEB, did='https://example.org')

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This is not a correct DID web'])

    def test_a_did_that_is_already_registered_is_refused(self):
        DID.objects.create(label='Taken', type=DID.Types.WEB, did=self.web_did())
        form = self.form(label='Ours', type=DID.Types.WEB, did=self.web_did())

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This DID exist already'])

    def test_a_did_registered_by_someone_else_is_refused_too(self):
        # The did lookup is global, unlike the label one.
        other = factories.make_user('other@example.org', 'testpass12')
        DID.objects.create(
            label='Theirs', type=DID.Types.WEB, did=self.web_did(), user=other
        )
        form = self.form(label='Ours', type=DID.Types.WEB, did=self.web_did())

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This DID exist already'])

    def test_a_label_you_already_used_is_refused(self):
        factories.make_did(label='Mine', user=self.user)
        form = self.form(label='Mine', type=DID.Types.KEY)

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This Label exist already'])

    def test_a_label_someone_else_used_is_free(self):
        other = factories.make_user('other@example.org', 'testpass12')
        factories.make_did(label='Mine', user=other)
        form = self.form(label='Mine', type=DID.Types.KEY)

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_a_label_the_organisation_used_is_free(self):
        factories.make_did(label='Mine')
        form = self.form(label='Mine', type=DID.Types.KEY)

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_without_a_label_the_form_refuses_before_reaching_clean(self):
        form = self.form(type=DID.Types.KEY)

        self.assertFalse(form.is_valid())
        self.assertIn('label', form.errors)

    def test_a_missing_type_crashes_instead_of_being_reported(self):
        # type is required, so it is absent from cleaned_data, and clean()
        # calls int() on it anyway.
        with self.assertRaises(TypeError):
            self.form(label='Ours').is_valid()

    def test_the_form_still_needs_the_view_that_feeds_it(self):
        # The admin twin grew an "if self.instance.key_material" guard around
        # get_did_document() and stands on its own now; this copy did not, so
        # a bare DID() still raises from the crypto layer on the first
        # did:web: nacl.exceptions.ValueError, "salt must be exactly 16 bytes
        # long", because the user has no vault to decrypt the key material
        # nobody has generated.
        form = DIDForm(
            data={'label': 'Ours', 'type': DID.Types.WEB, 'did': self.web_did()},
            user=self.user,
        )

        with self.assertRaises(ValueError):
            form.is_valid()

    def test_without_commit_nothing_is_stored(self):
        form = self.form(label='Ours', type=DID.Types.WEB, did=self.web_did())
        self.assertTrue(form.is_valid(), form.errors.as_text())

        self.assertIsNone(form.save(commit=False))
        self.assertFalse(DID.objects.filter(label='Ours').exists())

    def test_a_double_path_under_our_own_domain_is_accepted(self):
        form = self.form(
            label='Ours', type=DID.Types.WEB, did=self.web_did(path='dids:abc')
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_a_deeper_path_under_our_own_domain_is_refused(self):
        form = self.form(
            label='Ours', type=DID.Types.WEB, did=self.web_did(path='dids:abc:xyz')
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            errors(form),
            ['Only a double path level is permitted for this domain.'],
        )
