"""What the Verifier stores when a wallet answers.

``OAuth2VPToken`` holds the presentation that came back and the result of
verifying it. Two things make it worth pinning line by line:

* the link to the ``Authorization`` is rebuilt in ``__init__`` from a ``code``
  keyword, so it behaves differently depending on how the row is obtained;
* ``verifing()`` writes the *boolean* returned by ``pyvckit`` into a
  ``CharField``, and every reader of that field assumes something else.
"""
import json

from unittest.mock import patch

from django.test import override_settings

from oidc4vp.models import Authorization, OAuth2VPToken
from test_support import factories
from test_support.base import IdHubBaseTestCase, IdHubTestCase


VP = json.dumps({
    '@context': ['https://www.w3.org/2018/credentials/v1'],
    'type': ['VerifiablePresentation'],
    'holder': 'did:key:z6MkpEZ',
    'verifiableCredential': [
        {'credentialSubject': {'firstName': 'First'}},
        {'credentialSubject': {'firstName': 'Last', 'email': 'last@example.org'}},
    ],
})


class AuthorizationLinkTest(IdHubBaseTestCase):
    def setUp(self):
        super().setUp()
        self.authorization = Authorization.objects.create(
            presentation_definition='["Membership Card"]'
        )

    def test_the_code_keyword_resolves_the_authorization(self):
        token = OAuth2VPToken(vp_token=VP, code=self.authorization.code)

        self.assertEqual(token.authorization, self.authorization)
        self.assertEqual(token.code, self.authorization.code)

    def test_an_unknown_code_leaves_no_authorization(self):
        token = OAuth2VPToken(vp_token=VP, code='not-a-known-code')

        self.assertIsNone(token.authorization)
        self.assertEqual(token.code, '')

    def test_without_a_code_there_is_no_authorization(self):
        self.assertIsNone(OAuth2VPToken(vp_token=VP).authorization)

    def test_an_explicit_authorization_is_overwritten_by_the_code_lookup(self):
        # __init__ assigns unconditionally, so the keyword argument any other
        # model would honour is discarded.
        token = OAuth2VPToken(vp_token=VP, authorization=self.authorization)

        self.assertIsNone(token.authorization)

    def test_reading_the_row_back_from_the_database_drops_the_link(self):
        # Model.from_db() goes through __init__, which receives no code and
        # therefore resets the foreign key it has just loaded.
        token = OAuth2VPToken(vp_token=VP, code=self.authorization.code)
        token.save()

        self.assertIsNone(OAuth2VPToken.objects.get(pk=token.pk).authorization)
        self.assertEqual(
            Authorization.objects.get(pk=self.authorization.pk).vp_tokens.count(),
            1,
        )


class VerifyingTest(IdHubBaseTestCase):
    def setUp(self):
        super().setUp()
        self.token = OAuth2VPToken(vp_token=VP)
        patcher = patch('oidc4vp.models.verify_vp_signature')
        self.verify = patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_valid_presentation_stores_the_boolean_not_the_report(self):
        self.verify.return_value = (True, 'Presentation and all included are valid')
        self.token.verifing()

        self.assertIs(self.token.result_verify, True)

    def test_the_reason_a_verification_failed_is_thrown_away(self):
        self.verify.return_value = (False, 'Credential #0 Invalid: expired')
        self.token.verifing()

        self.assertIs(self.token.result_verify, False)
        self.assertNotIn('expired', str(self.token.result_verify))

    def test_an_error_inside_the_library_is_not_caught(self):
        self.verify.side_effect = ValueError('malformed jws')
        with self.assertRaises(ValueError):
            self.token.verifing()

    def test_the_whole_presentation_is_handed_over_unparsed(self):
        self.verify.return_value = (True, 'ok')
        self.token.verifing()

        self.verify.assert_called_once_with(VP)


class RealVerificationTest(IdHubTestCase):
    """One round trip against pyvckit, with a presentation we really signed."""

    def test_a_presentation_signed_by_the_holder_verifies(self):
        credential = factories.make_issued_credential(self.user)
        vp = factories.make_presentation(self.user, [credential])

        token = OAuth2VPToken(vp_token=vp)
        token.verifing()

        self.assertIs(token.result_verify, True)

    def test_a_tampered_presentation_does_not(self):
        credential = factories.make_issued_credential(self.user)
        vp = json.loads(factories.make_presentation(self.user, [credential]))
        vp['verifiableCredential'][0]['credentialSubject']['firstName'] = 'Someone'

        token = OAuth2VPToken(vp_token=json.dumps(vp))
        token.verifing()

        self.assertIs(token.result_verify, False)


class ResultVerifyTest(IdHubBaseTestCase):
    """``get_result_verify`` expects json and gets a boolean.

    It has no callers in production, which is why nobody has met the error.
    """

    def test_an_unverified_token_reports_nothing(self):
        self.assertEqual(OAuth2VPToken(vp_token=VP).get_result_verify(), {})

    def test_the_boolean_left_by_verifing_cannot_be_parsed(self):
        token = OAuth2VPToken(vp_token=VP, result_verify=True)

        with self.assertRaises(TypeError):
            token.get_result_verify()

    def test_the_string_the_database_returns_cannot_be_parsed_either(self):
        token = OAuth2VPToken(vp_token=VP, result_verify=True)
        token.save()

        stored = OAuth2VPToken.objects.get(pk=token.pk)
        self.assertEqual(stored.result_verify, 'True')
        with self.assertRaises(json.JSONDecodeError):
            stored.get_result_verify()


@override_settings(OIDC_REDIRECT=False)
class ResponseVerifyTest(IdHubBaseTestCase):
    """Only the verification verdict; the redirection has its own class.

    The setting is pinned here because a successful verification asks for a
    redirect url, and building one needs an authorization.
    """

    def test_an_unverified_token_reports_a_failure(self):
        response = OAuth2VPToken(vp_token=VP).get_response_verify()

        self.assertEqual(response['verify'], 'Error, Failed verification')
        self.assertEqual(response['redirect_uri'], '')
        self.assertEqual(response['response'], '')

    def test_the_verify_field_always_carries_the_comma_the_caller_splits_on(self):
        # AuthorizeView.form_valid does result, msg = verify.split(","), so the
        # separator is part of the contract even when nothing was verified.
        for token in (
            OAuth2VPToken(vp_token=VP),
            OAuth2VPToken(vp_token=VP, result_verify=True),
        ):
            with self.subTest(result_verify=token.result_verify):
                self.assertIn(',', token.get_response_verify()['verify'])

    def test_a_verified_token_reports_success(self):
        token = OAuth2VPToken(vp_token=VP, result_verify=True)

        self.assertEqual(
            token.get_response_verify()['verify'], 'Ok, Correct verification'
        )

    def test_a_failed_verification_reads_as_correct_once_stored(self):
        # verifing() wrote the boolean False, the column gives back the string
        # "False", and a non-empty string is true: a presentation that failed
        # verification is reported as valid by anything that reloads the row.
        token = OAuth2VPToken(vp_token=VP, result_verify=False)
        token.save()

        stored = OAuth2VPToken.objects.get(pk=token.pk)
        self.assertEqual(stored.result_verify, 'False')
        self.assertEqual(
            stored.get_response_verify()['verify'], 'Ok, Correct verification'
        )


@override_settings(ALLOW_CODE_URI='https://testserver/oidc4vp/allow_code')
class RedirectUrlTest(IdHubBaseTestCase):
    def setUp(self):
        super().setUp()
        self.authorization = Authorization.objects.create(
            presentation_definition='["Membership Card"]'
        )
        self.token = OAuth2VPToken(
            vp_token=VP, result_verify=True, code=self.authorization.code
        )

    @override_settings(OIDC_REDIRECT=False)
    def test_without_the_setting_there_is_no_redirection(self):
        self.assertIsNone(self.token.get_redirect_url())
        self.assertEqual(self.token.get_response_verify()['redirect_uri'], '')

    @override_settings(OIDC_REDIRECT=True)
    def test_the_redirection_carries_the_code_to_allow_code(self):
        self.assertEqual(
            self.token.get_redirect_url(),
            'https://testserver/oidc4vp/allow_code?code={}'.format(
                self.authorization.code
            ),
        )
        self.assertEqual(
            self.token.get_response_verify()['redirect_uri'],
            self.token.get_redirect_url(),
        )

    @override_settings(OIDC_REDIRECT=True)
    def test_a_token_without_an_authorization_cannot_build_it(self):
        # Which includes every row read back from the database, since
        # __init__ drops the link.
        token = OAuth2VPToken(vp_token=VP, result_verify=True)

        with self.assertRaises(AttributeError):
            token.get_redirect_url()


class UserInfoTest(IdHubBaseTestCase):
    def test_the_subject_of_the_last_credential_is_reported(self):
        token = OAuth2VPToken(vp_token=VP)

        self.assertEqual(
            json.loads(token.get_user_info()),
            {'firstName': 'Last', 'email': 'last@example.org'},
        )

    def test_the_other_credentials_of_the_presentation_are_ignored(self):
        # promotion's ContractView reads vp_token.user_info to prefill a form,
        # so with more than one credential presented it only ever sees one.
        token = OAuth2VPToken(vp_token=VP)
        token.get_user_info()

        self.assertNotIn('First', token.user_info.values())

    def test_a_presentation_without_credentials_reports_null(self):
        token = OAuth2VPToken(vp_token=json.dumps({'holder': 'did:key:z6MkpEZ'}))

        self.assertEqual(token.get_user_info(), 'null')
        self.assertIsNone(token.user_info)

    def test_a_credential_without_a_subject_reports_null(self):
        token = OAuth2VPToken(
            vp_token=json.dumps({'verifiableCredential': [{'id': 'urn:uuid:1'}]})
        )

        self.assertEqual(token.get_user_info(), 'null')

    def test_a_presentation_that_is_not_json_raises(self):
        token = OAuth2VPToken(vp_token='not json at all')

        with self.assertRaises(json.JSONDecodeError):
            token.get_user_info()

    def test_the_whole_presentation_is_available_reindented(self):
        token = OAuth2VPToken(vp_token=VP)

        self.assertEqual(json.loads(token.get_user_info_all()), json.loads(VP))
        self.assertIn('\n  ', token.get_user_info_all())
