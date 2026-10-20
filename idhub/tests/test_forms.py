"""What the admin forms refuse, and how.

The happy path of most of these forms is already covered through the views
(``test_views.py``, ``test_credentials.py``, ``test_eidas1_issue.py``). What
was missing is the other half: the error branches, which is where the
surprises are.

Several of them turn a missing field into a crash instead of a form error,
because ``clean()`` subscripts ``cleaned_data`` for a field that failed its
own validation and is therefore absent.
"""
import json

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from openpyxl import Workbook, load_workbook
from openpyxl.packaging.custom import StringProperty

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from idhub.admin.forms import (
    DIDForm,
    EncryptionKeyForm,
    ImportForm,
    ImportSchemaForm,
    ImportSchemaUrlForm,
    MembershipForm,
    TermsConditionsForm,
    TermsConditionsForm2,
    UNTPCredentialImportForm,
    UserRolForm,
)
from idhub.services import VerificationService
from idhub.models import (
    DID,
    ContextFile,
    File_datas,
    Membership,
    Schemas,
    Service,
    UserRol,
    VerificableCredential,
)
from test_support import factories
from test_support.base import IdHubTestCase


SCHEMA_FILE = 'membership-card.json'
CONTEXT_FILE = 'membership-card.jsonld'
EXCEL_NAME = 'membership-card.xlsx'
OTHER_SCHEMA_FILE = 'course-credential.json'

# A host that is not settings.DOMAIN, so the offline http mock maps the url
# onto the file of the same name in the working tree.
REMOTE = 'https://schemas.example.org'

# did:web needs a dotted domain to pass sanitize_didweb, which 'testserver'
# is not.
WEB_DOMAIN = 'idhub.example.org'


def read_context():
    return Path(settings.BASE_DIR).joinpath('context', CONTEXT_FILE).read_bytes()


def read_excel(name=EXCEL_NAME):
    return Path(settings.BASE_DIR).joinpath(
        'examples', 'excel_examples', name
    ).read_bytes()


def stamp_excel(file_schema, name=EXCEL_NAME):
    """The example template plus the 'Schema' property clean_file_import reads."""
    workbook = load_workbook(BytesIO(read_excel(name)))
    workbook.custom_doc_props.append(
        StringProperty(name='Schema', value=file_schema)
    )
    out = BytesIO()
    workbook.save(out)
    return out.getvalue()


COLUMNS = [
    'organisation', 'membershipType', 'membershipId', 'affiliatedSince',
    'affiliatedUntil', 'typeOfPerson', 'identityDocType', 'identityNumber',
    'firstName', 'lastName', 'role', 'email',
]

ROW = {
    'organisation': 'Pangea',
    'membershipType': 'Employee',
    'membershipId': '1a',
    'affiliatedSince': '2023-01-01',
    'typeOfPerson': 'natural',
    'firstName': 'Pedro',
    'lastName': 'Lagasta',
    'email': 'user1@example.org',
}


def build_excel(rows, columns=COLUMNS):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(columns)
    for row in rows:
        sheet.append([row.get(column) for column in columns])
    out = BytesIO()
    workbook.save(out)
    return out.getvalue()


def errors(form):
    """The non-field errors, which is where a clean() refusal lands."""
    return form.errors.get('__all__', [])


class UnreadableFile(SimpleUploadedFile):
    """An upload that passes field validation and then fails to be read."""

    def read(self, *args, **kwargs):
        raise OSError('the upload went away')


class EncryptionKeyFormTest(IdHubTestCase):
    """The form that unlocks the whole instance.

    It validates the typed key by decrypting the first DID with it, and it
    has to leave the cache as it found it: the key only becomes current in
    ``save()``.
    """

    def form(self, **data):
        return EncryptionKeyForm(data=data)

    def test_a_missing_key_crashes_instead_of_being_reported(self):
        # key is required, so it is not in cleaned_data when it is empty, and
        # clean() subscripts it anyway.
        with self.assertRaises(KeyError):
            self.form(key='').is_valid()

    def test_any_key_is_accepted_while_there_is_nothing_to_check_against(self):
        self.assertFalse(DID.objects.exists())
        self.assertTrue(self.form(key='whatever').is_valid())

    def test_the_first_key_is_the_one_the_first_did_is_built_with(self):
        form = self.form(key='a new key')
        form.is_valid()
        form.save()
        self.addCleanup(cache.delete, 'KEY_DIDS')

        did = DID.objects.get()
        self.assertEqual(did.label, 'Default')
        self.assertEqual(did.type, DID.Types.WEB)
        self.assertEqual(cache.get('KEY_DIDS'), 'a new key')

    def test_the_right_key_validates(self):
        factories.make_did()
        self.assertTrue(self.form(key=self.KEY_DIDS).is_valid())

    def test_a_wrong_key_is_reported(self):
        factories.make_did()
        form = self.form(key='not the key')

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['Key no valid!'])

    def test_validating_clears_the_key_in_the_cache_either_way(self):
        # clean() borrows the cache to try the key out and resets it to None
        # on both paths, so a logged-in admin loses the running key by
        # visiting the page -- it is only restored if the form is saved.
        factories.make_did()
        for key in (self.KEY_DIDS, 'not the key'):
            with self.subTest(key=key):
                self.set_key_dids(self.KEY_DIDS)
                self.form(key=key).is_valid()
                self.assertIsNone(cache.get('KEY_DIDS'))

    def test_nothing_is_written_when_the_caller_does_not_commit(self):
        form = self.form(key='a new key')
        form.is_valid()

        self.assertIsNone(form.save(commit=False))
        self.assertEqual(cache.get('KEY_DIDS'), self.KEY_DIDS)
        self.assertFalse(DID.objects.exists())

    def test_saving_does_not_create_a_second_default_did(self):
        existing = factories.make_did()
        form = self.form(key=self.KEY_DIDS)
        form.is_valid()
        form.save()
        self.addCleanup(cache.delete, 'KEY_DIDS')

        self.assertEqual([d.pk for d in DID.objects.all()], [existing.pk])


class TermsConditionsFormTest(IdHubTestCase):
    """The three policy checkboxes a user has to tick before anything else.

    This is the admin copy of the form; the holder one lives in
    ``idhub/user/forms.py`` and differs only in the css class of the link.
    """

    def form(self, **data):
        return TermsConditionsForm(data=data, user=self.user)

    def accepted(self):
        return {
            'accept_privacy': 'on',
            'accept_legal': 'on',
            'accept_cookies': 'on',
        }

    def test_the_three_policies_together_grant_consent(self):
        self.user.accept_gdpr = False
        self.user.save()
        form = self.form(**self.accepted())

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertTrue(form.save().accept_gdpr)
        self.user.refresh_from_db()
        self.assertTrue(self.user.accept_gdpr)

    def test_an_empty_submission_withdraws_consent(self):
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

        self.assertTrue(form.user.accept_gdpr)
        self.assertIsNone(form.save(commit=False))
        self.user.refresh_from_db()
        self.assertFalse(self.user.accept_gdpr)

    @override_settings(POLICY_PRIVACY='https://example.org/privacy')
    def test_the_admin_labels_carry_the_admin_button_class(self):
        label = self.form().privacy_label()

        self.assertIn('btn-green-admin', label)
        self.assertIn('https://example.org/privacy', label)


class TermsConditionsForm2Test(IdHubTestCase):
    """A single-checkbox variant of the form above that nobody uses.

    No view, template or test imports ``TermsConditionsForm2``: it is the
    earlier version of the consent page, left behind when the policies were
    split in three. It is pinned here because dead code that writes to
    ``accept_gdpr`` is worth noticing if it ever gets wired up again.
    """

    def form(self, **data):
        return TermsConditionsForm2(data=data, user=self.user)

    def test_ticking_the_only_checkbox_grants_consent(self):
        self.user.accept_gdpr = False
        self.user.save()
        form = self.form(accept='on')

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertTrue(form.save().accept_gdpr)
        self.user.refresh_from_db()
        self.assertTrue(self.user.accept_gdpr)

    def test_leaving_it_empty_withdraws_consent(self):
        form = self.form()

        self.assertTrue(form.is_valid(), form.errors.as_text())
        form.save()
        self.user.refresh_from_db()
        self.assertFalse(self.user.accept_gdpr)

    def test_without_a_user_the_form_crashes_instead_of_refusing(self):
        # user is popped with a None default, so a caller that forgets it gets
        # an AttributeError out of clean() instead of a form error.
        with self.assertRaises(AttributeError):
            TermsConditionsForm2(data={'accept': 'on'}).is_valid()

    def test_nothing_is_written_when_the_caller_does_not_commit(self):
        form = self.form(accept='on')
        form.is_valid()

        self.assertIsNone(form.save(commit=False))


class ImportSchemaFormTest(IdHubTestCase):
    """Uploading a schema, and optionally its @context, as files."""

    def form(self, schema=None, context=None, schema_name=SCHEMA_FILE):
        files = {}
        if schema is not None:
            files['schema_import'] = SimpleUploadedFile(schema_name, schema)
        if context is not None:
            files['context_import'] = SimpleUploadedFile(CONTEXT_FILE, context)
        return ImportSchemaForm(data={}, files=files)

    def schema_bytes(self, file_name=SCHEMA_FILE, **overrides):
        data = json.loads(factories.read_schema(file_name))
        for key, value in overrides.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        return json.dumps(data).encode()

    def test_a_schema_on_its_own_is_enough(self):
        form = self.form(schema=self.schema_bytes())

        self.assertTrue(form.is_valid(), form.errors.as_text())
        schema = form.save()
        self.assertEqual(schema.file_schema, SCHEMA_FILE)
        self.assertIsNone(schema.context)
        self.assertFalse(ContextFile.objects.exists())

    def test_a_missing_file_crashes_instead_of_being_reported(self):
        with self.assertRaises(KeyError):
            self.form().is_valid()

    def test_something_that_is_not_json_is_refused(self):
        form = self.form(schema=b'not json at all')

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This schema not is a json file'])

    def test_a_schema_without_a_title_is_refused(self):
        form = self.form(schema=self.schema_bytes(title=None))

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This is not a valid schema!'])

    def test_a_schema_without_a_name_is_refused(self):
        form = self.form(schema=self.schema_bytes(name=None))

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This is not a valid schema!'])

    def test_the_same_file_name_twice_is_refused(self):
        factories.make_schema(SCHEMA_FILE)
        form = self.form(schema=self.schema_bytes())

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['Schema exist!'])

    def test_a_context_is_only_stored_when_a_domain_is_given(self):
        # The view passes the domain in; without it the context file is read,
        # validated and then dropped on the floor.
        form = self.form(schema=self.schema_bytes(), context=read_context())
        self.assertTrue(form.is_valid(), form.errors.as_text())

        schema = form.save()
        self.assertIsNone(schema.context)
        self.assertFalse(ContextFile.objects.exists())

    def test_a_context_with_a_domain_is_published_under_our_own_url(self):
        form = self.form(schema=self.schema_bytes(), context=read_context())
        form.is_valid()
        schema = form.save(domain='https://{}'.format(settings.DOMAIN))

        context = ContextFile.objects.get()
        self.assertEqual(context.file_name, CONTEXT_FILE)
        self.assertIn(CONTEXT_FILE, schema.context)
        self.assertTrue(schema.context.startswith(
            'https://{}'.format(settings.DOMAIN)
        ))

    def test_a_context_that_is_not_json_is_refused(self):
        form = self.form(schema=self.schema_bytes(), context=b'not json')

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This context is no a valid jsonld'])

    def test_a_context_that_cannot_be_read_is_reported_as_invalid_jsonld(self):
        # The read is wrapped in an "except Exception: pass", so an upload
        # that dies mid-transfer leaves self.context without its "data" key
        # and the next block turns the KeyError into the jsonld message.
        files = {
            'schema_import': SimpleUploadedFile(SCHEMA_FILE, self.schema_bytes()),
            'context_import': UnreadableFile(CONTEXT_FILE, b'{}'),
        }
        form = ImportSchemaForm(data={}, files=files)

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This context is no a valid jsonld'])
        self.assertNotIn('data', form.context)

    def test_a_context_file_name_already_in_use_is_reused(self):
        # A context name that is taken is no longer refused: the stored row
        # wins, the upload is dropped, and both schemas point at the same url.
        factories.make_schema(SCHEMA_FILE)
        stored = ContextFile.objects.create(file_name=CONTEXT_FILE, data='{}')
        form = self.form(
            schema=self.schema_bytes(file_name=OTHER_SCHEMA_FILE),
            context=read_context(),
            schema_name=OTHER_SCHEMA_FILE,
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        schema = form.save(domain='https://{}'.format(settings.DOMAIN))

        self.assertEqual([c.pk for c in ContextFile.objects.all()], [stored.pk])
        self.assertEqual(ContextFile.objects.get().data, '{}')
        self.assertIn(CONTEXT_FILE, schema.context)


class ImportSchemaUrlFormTest(IdHubTestCase):
    """The same thing by url, which is what the pilot deployments use."""

    def setUp(self):
        super().setUp()
        # validate_safe_host resolves the host for real; the suite is offline.
        patcher = patch.object(VerificationService, 'validate_safe_host')
        patcher.start()
        self.addCleanup(patcher.stop)

    def form(self, **data):
        return ImportSchemaUrlForm(data=data)

    def valid_data(self, **overrides):
        data = {
            'schema_url': '{}/vc_schemas/{}'.format(REMOTE, SCHEMA_FILE),
            'context_url': '{}/context/{}'.format(REMOTE, CONTEXT_FILE),
        }
        data.update(overrides)
        return data

    def test_both_urls_are_fetched_and_the_context_url_is_kept_verbatim(self):
        data = self.valid_data()
        form = self.form(**data)

        self.assertTrue(form.is_valid(), form.errors.as_text())
        schema = form.save()
        self.assertEqual(schema.file_schema, SCHEMA_FILE)
        self.assertEqual(schema.context, data['context_url'])
        self.assertEqual(schema.validation_url, data['schema_url'])

    def test_the_context_url_is_optional(self):
        form = self.form(**self.valid_data(context_url=''))

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.save().context, '')

    def test_the_schema_url_is_required(self):
        form = self.form(**self.valid_data(schema_url=''))

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['schema_url'], ['This field is required.'])

    def test_a_schema_url_nothing_answers_is_reported(self):
        with patch('idhub.admin.forms.requests.get',
                   side_effect=requests.RequestException):
            form = self.form(**self.valid_data())

            self.assertFalse(form.is_valid())
        self.assertEqual(
            errors(form),
            ['Could not download the schema from the provided URL.'],
        )

    def test_a_context_url_nothing_answers_is_reported(self):
        form = self.form(**self.valid_data(
            context_url='{}/context/nothing-here.jsonld'.format(REMOTE)
        ))

        with patch('idhub.admin.forms.requests.get',
                   side_effect=self.schema_ok_context_down):
            self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['The context URL is not accessible.'])

    def schema_ok_context_down(self, url, **kwargs):
        if '/context/' in url:
            raise requests.RequestException
        return requests.Session().get(url, **kwargs)

    def test_a_url_without_an_extension_gets_json_appended(self):
        # The name the schema is filed under comes from the url, not from the
        # document, so an extensionless url still produces a .json row.
        form = self.form(**self.valid_data(
            schema_url='https://w3id.org/security/v2'
        ))

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data['file_name'], 'v2.json')

    def answer(self, body, status_code=200):
        response = requests.Response()
        response.status_code = status_code
        response._content = body
        return response

    def serving(self, payload):
        """Every url answers with the given document."""
        return patch(
            'idhub.admin.forms.requests.get',
            return_value=self.answer(json.dumps(payload).encode()),
        )

    def untitled_schema(self, **properties):
        """A valid json schema with neither a title nor a name."""
        return {'type': 'object', 'properties': properties}

    def test_a_url_that_cannot_be_parsed_is_reported(self):
        # Unreachable through the field: URLField validates the url before
        # clean() ever gets to urlparse it, so the only way in is a patch.
        with patch('idhub.admin.forms.urlparse', side_effect=ValueError):
            form = self.form(**self.valid_data())

            self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This schema not is a json file'])

    def test_a_host_the_safety_check_refuses_is_reported(self):
        with patch.object(VerificationService, 'validate_safe_host',
                          side_effect=ValueError('private address')):
            form = self.form(**self.valid_data())

            self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['Invalid schema URL: private address'])

    def test_a_schema_that_is_not_json_is_blamed_on_the_download(self):
        # The "not a valid JSON file" message below it is unreachable:
        # res.json() raises requests.JSONDecodeError, which is both a
        # ValueError and a RequestException, and the download branch is
        # written first, so a readable url serving garbage is reported as
        # unreachable instead.
        with patch('idhub.admin.forms.requests.get',
                   return_value=self.answer(b'not json at all')):
            form = self.form(**self.valid_data())

            self.assertFalse(form.is_valid())
        self.assertEqual(
            errors(form),
            ['Could not download the schema from the provided URL.'],
        )

    def test_the_invalid_json_messages_need_a_plain_value_error(self):
        # What is left of those two branches, pinned behind a json() that
        # raises a bare ValueError.
        cases = [
            ('schema_url', 'The downloaded schema is not a valid JSON file.'),
            ('context_url', 'The context URL is not a valid JSON file.'),
        ]
        for field, message in cases:
            with self.subTest(field=field):
                response = self.answer(json.dumps(self.untitled_schema()).encode())
                def json_of(url, **kwargs):
                    if url == self.valid_data()[field]:
                        return self.plain_value_error()
                    return response

                with patch('idhub.admin.forms.requests.get', side_effect=json_of):
                    form = self.form(**self.valid_data())

                    self.assertFalse(form.is_valid())
                self.assertEqual(errors(form), [message])

    def plain_value_error(self):
        return Mock(raise_for_status=Mock(), json=Mock(side_effect=ValueError))

    def test_a_document_that_is_not_a_valid_schema_is_refused(self):
        with self.serving({'type': 123}):
            form = self.form(**self.valid_data(context_url=''))

            self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This is not a valid schema!'])

    def test_a_validator_that_blows_up_is_reported_the_same_way(self):
        with self.serving(self.untitled_schema()), \
             patch('idhub.admin.forms.credtools.validate_schema',
                   side_effect=Exception('boom')):
            form = self.form(**self.valid_data(context_url=''))

            self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This is not a valid schema!'])

    def test_a_schema_with_no_title_is_named_after_its_credential_types(self):
        schema = self.untitled_schema(
            type={'default': ['DigitalProductPassport', 'VerifiableCredential']}
        )
        with self.serving(schema):
            form = self.form(**self.valid_data(context_url=''))
            self.assertTrue(form.is_valid(), form.errors.as_text())

        # VerifiableCredential is moved to the front, whatever the document
        # says, because it is the type every credential has.
        self.assertEqual(
            form.save().name, 'VerifiableCredential - DigitalProductPassport'
        )

    def test_a_schema_whose_types_say_nothing_of_credentials_keeps_their_order(self):
        schema = self.untitled_schema(
            type={'default': ['DigitalProductPassport', 'ProductPassport']}
        )
        with self.serving(schema):
            form = self.form(**self.valid_data(context_url=''))
            self.assertTrue(form.is_valid(), form.errors.as_text())

        self.assertEqual(
            form.save().name, 'DigitalProductPassport - ProductPassport'
        )

    def test_a_schema_with_neither_title_nor_types_is_named_after_the_file(self):
        with self.serving(self.untitled_schema(type={'default': {}})):
            form = self.form(**self.valid_data(context_url=''))
            self.assertTrue(form.is_valid(), form.errors.as_text())

        self.assertEqual(form.save().name, SCHEMA_FILE)

    def test_importing_the_same_schema_twice_is_refused(self):
        # The duplicate guard compares validation_url, which is the column
        # save() writes verbatim, so the second import is caught.
        form = self.form(**self.valid_data())
        self.assertTrue(form.is_valid(), form.errors.as_text())
        form.save()

        form = self.form(**self.valid_data())

        self.assertFalse(form.is_valid())
        self.assertEqual(
            errors(form), ['A Schema with this URL already exists!']
        )
        self.assertEqual(Schemas.objects.filter(file_schema=SCHEMA_FILE).count(), 1)


class ImportFormErrorsTest(IdHubTestCase):
    """The spreadsheet importer: everything that is not a clean import."""

    def setUp(self):
        super().setUp()
        self.schema = factories.make_schema(SCHEMA_FILE)
        self.issuer = factories.make_did(label='Issuer')

    def form(self, excel=None, excel_name=EXCEL_NAME, **overrides):
        data = {'did': self.issuer.did, 'schema': self.schema.id}
        data.update(overrides)
        if excel is None:
            excel = read_excel()
        return ImportForm(
            data=data,
            files={'file_import': SimpleUploadedFile(excel_name, excel)},
        )

    def test_the_example_spreadsheet_imports(self):
        self.assertTrue(self.form().is_valid())

    def test_a_did_that_is_not_ours_crashes_instead_of_being_reported(self):
        # The choices only hold our own available dids, so anything else
        # fails field validation and leaves no 'did' in cleaned_data --
        # which clean() subscripts regardless. The "Did not valid!" message
        # it means to raise is unreachable.
        with self.assertRaises(KeyError):
            self.form(did='did:web:elsewhere.example.org:dids:1').is_valid()

    def test_a_user_did_cannot_be_used_to_issue(self):
        mine = factories.make_did(label='Mine', user=self.user)

        with self.assertRaises(KeyError):
            self.form(did=mine.did).is_valid()

    def test_the_please_choose_placeholder_is_refused(self):
        form = self.form(schema=0)

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['schema'], ['Schema is not valid!'])

    def test_a_file_that_is_not_a_spreadsheet_is_refused(self):
        form = self.form(excel=b'not a spreadsheet')

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['file_import'], ['This file does not a excel valid!']
        )

    def test_none_of_the_shipped_templates_is_stamped_with_its_schema(self):
        # clean_file_import compares the schema name against the 'Schema'
        # custom document property, and that is the only cheap check it has.
        # None of the templates the project hands out carries one, so the
        # check is dead for every real import and a mismatch is only caught
        # row by row.
        for name in ('membership-card', 'course-credential', 'federation-membership'):
            with self.subTest(excel=name):
                workbook = load_workbook(
                    BytesIO(read_excel('{}.xlsx'.format(name)))
                )
                self.assertNotIn('Schema', workbook.custom_doc_props.names)

    def test_a_spreadsheet_stamped_with_another_schema_is_refused(self):
        form = self.form(excel=stamp_excel(OTHER_SCHEMA_FILE))

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['file_import'],
            ['This File does not correspond to this scheme!'],
        )

    def test_a_spreadsheet_stamped_with_the_right_schema_is_accepted(self):
        self.assertTrue(self.form(excel=stamp_excel(SCHEMA_FILE)).is_valid())

    def test_a_spreadsheet_for_another_schema_is_caught_row_by_row(self):
        other = factories.make_schema(OTHER_SCHEMA_FILE)
        form = self.form(schema=other.id)

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['file_import'],
            ["line 2: 'personalIdentifier' is a required property"],
        )

    def test_a_refused_row_is_recorded_as_a_failed_import(self):
        form = self.form(excel=read_excel('federation-membership.xlsx'))

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['file_import'],
            ["line 2: 'organisation' is a required property"],
        )
        upload = File_datas.objects.get()
        self.assertEqual(upload.file_name, EXCEL_NAME)
        self.assertFalse(upload.success)

    def test_a_spreadsheet_with_only_a_header_row_is_refused(self):
        form = self.form(excel=build_excel([]))

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['file_import'], ['The file you try to import is empty!']
        )
        self.assertFalse(File_datas.objects.get().success)

    def test_a_column_the_schema_never_heard_of_is_refused(self):
        form = self.form(excel=build_excel(
            [dict(ROW, nickname='pedrito')], COLUMNS + ['nickname']
        ))

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['file_import'], [
            "line 2: Additional properties are not allowed "
            "('nickname' was unexpected)"
        ])

    def test_a_required_column_that_is_not_there_names_the_line(self):
        form = self.form(excel=build_excel(
            [{k: v for k, v in ROW.items() if k != 'organisation'}],
            [c for c in COLUMNS if c != 'organisation'],
        ))

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['file_import'],
            ["line 2: 'organisation' is a required property"],
        )

    def test_a_number_where_the_schema_wants_a_string_is_coerced(self):
        # clean_file_import casts every column the schema calls a string,
        # which is what keeps a numeric membership id from being refused.
        form = self.form(excel=build_excel([dict(ROW, membershipId=42)]))

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.rows[self.user_of(form)]['membershipId'], '42')

    def user_of(self, form):
        return next(iter(form.rows))

    def test_a_did_deleted_while_the_page_was_open_is_reported(self):
        # The only way into "Did not valid!": the choices are built when the
        # page is rendered, so a did another admin removes in the meantime is
        # still submittable and only clean() notices it is gone.
        form = self.form()
        self.issuer.delete()

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['Did not valid!'])

    def test_a_schema_whose_subject_cannot_be_read_crashes_the_import(self):
        # clean_schema sets self._schema before reading the subject schema, so
        # the "Schema not valid!" error it raises when that read fails is never
        # shown: clean_file_import runs next, finds self._schema set and
        # self.json_schema missing, and the admin gets a 500 instead.
        with patch.object(Schemas, 'get_credential_subject_schema',
                          side_effect=Exception('boom')):
            with self.assertRaises(AttributeError):
                self.form().is_valid()

    def test_a_row_with_nothing_in_it_is_skipped(self):
        # It has to come before a filled one: pandas drops the empty rows at
        # the end of the sheet, so a trailing one never reaches the loop.
        form = self.form(excel=build_excel([{}, ROW]))

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(len(form.rows), 1)

    def test_a_row_without_a_user_is_dropped(self):
        # validate_jsonld either raises or hands back a user, so the guard
        # around its return value is unreachable; this is what it would do.
        with patch.object(ImportForm, 'validate_jsonld', return_value=None):
            form = self.form()

            self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.rows, {})

    def test_nothing_is_written_when_the_caller_does_not_commit(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors.as_text())

        self.assertIsNone(form.save(commit=False))
        self.assertFalse(VerificableCredential.objects.exists())
        self.assertFalse(File_datas.objects.exists())

    @override_settings(DPP=True, API_DLT_URL='http://dlt.example.org')
    def test_a_dpp_deployment_registers_every_new_holder_on_the_ledger(self):
        # Importing a spreadsheet creates the holders it names, and with each
        # of them a default did. On a DPP deployment that did is a WEBETH one,
        # so set_did() has to reach the ledger for an ethereum account before
        # the import can go through.
        def answer(payload):
            return Mock(json=Mock(return_value=payload))

        def get(url, *args, **kwargs):
            if url.endswith('/getTa'):
                return answer({'data': {'root_pub_key': '0x' + 'b' * 40}})
            return answer({'data': {'chain_id': 1337}})

        # set_did() asserts both lengths, 80 and 42, before storing them.
        registered = answer({'data': {
            'api_token': 't' * 80, 'eth_pub_key': '0x' + 'a' * 40,
        }})
        with patch('idhub.models.requests.post', return_value=registered) as post, \
             patch('idhub.models.requests.get', side_effect=get):
            form = self.form()

            self.assertTrue(form.is_valid(), form.errors.as_text())

        post.assert_called_once_with('http://dlt.example.org/registerUser')
        did = DID.objects.get(user__isnull=False)
        self.assertEqual(did.label, 'dpp')
        self.assertEqual(did.type, DID.Types.WEBETH)

    def test_a_file_that_is_not_a_spreadsheet_leaves_no_trace(self):
        # The excel branch raises before self.file_name is set, so unlike a
        # bad row this failure is not recorded anywhere.
        self.form(excel=b'not a spreadsheet').is_valid()

        self.assertFalse(File_datas.objects.exists())
        self.assertFalse(DID.objects.filter(user__isnull=False).exists())


@override_settings(DOMAIN=WEB_DOMAIN)
class DIDFormTest(IdHubTestCase):
    """Registering an organisation DID.

    The form cannot generate key material: ``DidRegisterView`` builds a
    ``DID(type=WEB)``, calls ``set_did()`` on it and keeps it in the session,
    and the form edits *that*. Every test here hands it the same half-built
    instance the view would.
    """

    def setUp(self):
        super().setUp()
        # create_user/make_organization leave this unset, and the did's key
        # material is encrypted against it.
        self.org.set_encrypted_sensitive_data()
        self.org.save()

    def pregenerated(self):
        instance = DID(type=DID.Types.WEB)
        instance.set_did()
        return instance

    def form(self, instance=None, **data):
        if instance is None:
            instance = self.pregenerated()
        return DIDForm(instance=instance, data=data)

    def web_did(self, domain=WEB_DOMAIN, path='abc123'):
        return 'did:web:{}:{}'.format(domain, path)

    def test_a_did_on_our_own_domain_is_available(self):
        form = self.form(label='Ours', type=DID.Types.WEB, did=self.web_did())

        self.assertTrue(form.is_valid(), form.errors.as_text())
        did = form.save()
        self.assertEqual(did.did, self.web_did())
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

    def test_the_domain_is_lowercased_but_the_path_is_not(self):
        form = self.form(
            label='Mixed',
            type=DID.Types.WEB,
            did='did:web:{}:AbC123'.format(WEB_DOMAIN.upper()),
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.save().did, self.web_did(path='AbC123'))

    def test_a_key_did_is_generated_and_the_typed_did_is_ignored(self):
        form = self.form(label='Key', type=DID.Types.KEY, did='did:web:nonsense')

        self.assertTrue(form.is_valid(), form.errors.as_text())
        did = form.save()
        self.assertTrue(did.did.startswith('did:key:'))
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
            instance=instance, label='Ours', type=DID.Types.WEB,
            did=self.web_did(),
        )
        form.is_valid()

        self.assertIs(form.instance, instance)
        self.assertNotEqual(form.save().did, generated)

    def test_a_web_did_without_a_did_is_refused(self):
        form = self.form(label='Ours', type=DID.Types.WEB)

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This field is required'])

    def test_something_that_is_not_a_did_web_is_refused(self):
        form = self.form(label='Ours', type=DID.Types.WEB, did='https://example.org')

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This is not a correct DID web'])

    def test_a_double_path_under_our_own_domain_is_accepted(self):
        form = self.form(
            label='Ours', type=DID.Types.WEB, did=self.web_did(path='dids:abc'),
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_a_deeper_path_under_our_own_domain_is_refused(self):
        form = self.form(
            label='Ours', type=DID.Types.WEB,
            did=self.web_did(path='dids:abc:xyz'),
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            errors(form),
            ['Only a double path level is permitted for this domain.'],
        )

    def test_a_domain_without_a_dot_is_refused(self):
        form = self.form(
            label='Ours', type=DID.Types.WEB, did='did:web:localhost:abc',
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['Is not a valid url'])

    def test_the_same_did_twice_is_refused(self):
        first = self.form(label='Ours', type=DID.Types.WEB, did=self.web_did())
        first.is_valid()
        first.save()

        second = self.form(label='Again', type=DID.Types.WEB, did=self.web_did())
        self.assertFalse(second.is_valid())
        self.assertEqual(errors(second), ['This DID exist already'])

    def test_an_organisation_label_already_in_use_is_refused(self):
        factories.make_did(label='Taken')
        form = self.form(label='Taken', type=DID.Types.KEY)

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['This Label exist already'])

    def test_a_label_a_user_already_uses_is_not_a_conflict(self):
        factories.make_did(label='Default', user=self.user)
        form = self.form(label='Default', type=DID.Types.KEY)

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_a_missing_type_crashes_instead_of_being_reported(self):
        # type is required, so it is absent from cleaned_data, and clean()
        # calls int() on it anyway.
        with self.assertRaises(TypeError):
            self.form(label='Ours').is_valid()

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

    def test_nothing_is_written_when_the_caller_does_not_commit(self):
        form = self.form(label='Ours', type=DID.Types.WEB, did=self.web_did())
        self.assertTrue(form.is_valid(), form.errors.as_text())

        self.assertIsNone(form.save(commit=False))
        self.assertFalse(DID.objects.exists())

    def test_the_form_no_longer_needs_the_view_that_feeds_it(self):
        # It used to raise from the crypto layer on a bare DID(), because
        # get_did_document() was called with key material nobody had
        # generated. Now it stands on its own as a plain ModelForm.
        form = DIDForm(data={
            'label': 'Ours', 'type': DID.Types.WEB, 'did': self.web_did(),
        })

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.save().did, self.web_did())


class MembershipFormTest(IdHubTestCase):
    """Memberships overlap in time, which is what this form is about."""

    def form(self, instance=None, **data):
        if instance is None:
            instance = Membership(user=self.user)
        return MembershipForm(instance=instance, data=data)

    def membership(self, user=None, type=Membership.Types.MEMBER, **dates):
        return Membership.objects.create(
            user=user or self.user, type=type, **dates
        )

    def test_a_closed_period_is_accepted(self):
        form = self.form(
            type=Membership.Types.MEMBER,
            start_date='2026-01-01',
            end_date='2026-12-31',
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.save().user, self.user)

    def test_an_open_period_is_accepted(self):
        form = self.form(type=Membership.Types.MEMBER, start_date='2026-01-01')

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertIsNone(form.save().end_date)

    def test_an_end_before_the_start_is_refused(self):
        form = self.form(
            type=Membership.Types.MEMBER,
            start_date='2026-12-31',
            end_date='2026-01-01',
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['end_date'], ['The end date is less than the start date']
        )

    def test_a_missing_start_date_crashes_instead_of_being_reported(self):
        # start_date is blank=True on the model, so an empty one validates as
        # None and goes straight into a start_date__lte lookup, which the orm
        # refuses. A membership with no dates is unreachable through the form.
        with self.assertRaises(ValueError):
            self.form(type=Membership.Types.MEMBER).is_valid()

    def test_a_missing_type_crashes_instead_of_being_reported(self):
        with self.assertRaises(KeyError):
            self.form(start_date='2026-01-01').is_valid()

    def test_a_period_inside_an_open_one_is_refused(self):
        self.membership(start_date='2026-01-01')
        form = self.form(
            type=Membership.Types.MEMBER,
            start_date='2026-06-01',
            end_date='2026-07-01',
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['end_date'], ['This membership already exists!']
        )

    def test_two_overlapping_closed_periods_are_refused(self):
        self.membership(start_date='2026-01-01', end_date='2026-06-30')
        form = self.form(
            type=Membership.Types.MEMBER,
            start_date='2026-06-01',
            end_date='2026-12-31',
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['end_date'], ['This membership already exists!']
        )

    def test_two_consecutive_periods_touching_on_one_day_are_refused(self):
        # The overlap test is inclusive on both ends, so handing over on the
        # same day counts as a clash.
        self.membership(start_date='2026-01-01', end_date='2026-06-30')
        form = self.form(
            type=Membership.Types.MEMBER,
            start_date='2026-06-30',
            end_date='2026-12-31',
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['end_date'], ['This membership already exists!']
        )

    def test_a_second_period_after_a_closed_one_is_accepted(self):
        self.membership(start_date='2026-01-01', end_date='2026-06-30')
        form = self.form(
            type=Membership.Types.MEMBER,
            start_date='2026-07-01',
            end_date='2026-12-31',
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_an_open_period_that_would_swallow_a_later_one_is_refused(self):
        self.membership(start_date='2026-06-01', end_date='2026-12-31')
        form = self.form(type=Membership.Types.MEMBER, start_date='2026-01-01')

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['end_date'], ['This membership already exists!']
        )

    def test_an_open_period_starting_inside_a_closed_one_is_accepted(self):
        # The open-ended branch only looks for rows starting *at or after*
        # the new start date, so an open membership that begins in the middle
        # of an existing closed one slips through and the two overlap.
        self.membership(start_date='2026-01-01', end_date='2026-12-31')
        form = self.form(type=Membership.Types.MEMBER, start_date='2026-06-01')

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_another_type_of_membership_never_clashes(self):
        self.membership(type=Membership.Types.EMPLOYEE, start_date='2026-01-01')
        form = self.form(
            type=Membership.Types.MEMBER,
            start_date='2026-06-01',
            end_date='2026-07-01',
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_another_person_never_clashes(self):
        self.membership(user=self.admin_user, start_date='2026-01-01')
        form = self.form(
            type=Membership.Types.MEMBER,
            start_date='2026-06-01',
            end_date='2026-07-01',
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_editing_a_row_does_not_clash_with_itself(self):
        existing = self.membership(start_date='2026-01-01')
        form = self.form(
            instance=existing,
            type=Membership.Types.MEMBER,
            start_date='2026-01-01',
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())


class UserRolFormTest(IdHubTestCase):
    """Granting a user access to a service."""

    def setUp(self):
        super().setUp()
        self.service = Service.objects.create(
            domain='service.example.org', description='A service'
        )

    def form(self, user=None, **data):
        return UserRolForm(instance=UserRol(user=user or self.user), data=data)

    def test_a_service_can_be_granted(self):
        form = self.form(service=self.service.id)

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.save().service, self.service)

    def test_a_missing_service_is_reported(self):
        form = self.form()

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['service'], ['This field is required.'])

    def test_a_service_the_user_already_has_is_not_offered(self):
        UserRol.objects.create(user=self.user, service=self.service)
        choices = list(self.form(service=self.service.id).fields['service'].choices)

        self.assertEqual([value for value, label in choices], [''])

    def test_but_narrowing_the_choices_is_only_cosmetic(self):
        # __init__ narrows the choices the widget renders; validation goes
        # through the field's own queryset, which is untouched. So a value
        # the dropdown does not offer still reaches clean_service, and it is
        # that method -- not the narrowing -- that stops the duplicate.
        UserRol.objects.create(user=self.user, service=self.service)
        form = self.form(service=self.service.id)

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['service'], [
            'Is not possible to have a duplicate role'
        ])

    def test_the_narrowing_is_per_user(self):
        UserRol.objects.create(user=self.admin_user, service=self.service)
        form = self.form(service=self.service.id)

        self.assertTrue(form.is_valid(), form.errors.as_text())

    def test_editing_an_existing_grant_sees_every_service(self):
        # The queryset is only narrowed for a new row, so an edit form offers
        # the service that is already granted.
        grant = UserRol.objects.create(user=self.user, service=self.service)
        form = UserRolForm(instance=grant, data={'service': self.service.id})
        choices = [value for value, label in form.fields['service'].choices]

        self.assertIn(self.service.id, choices)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['service'], [
            'Is not possible to have a duplicate role'
        ])


class UNTPCredentialImportFormTest(IdHubTestCase):
    """Issuing a UNTP credential out of a credentialSubject document.

    The document is uploaded as a json file, so almost everything this form
    does is deciding what shape it has: one subject or several, with an id of
    its own or with one this instance is about to mint for it. The issuance
    itself is a call to the service, faked here, because what is interesting
    is which subject identity the credential ends up pointing at.
    """

    SUBJECT_ID = 'did:web:testserver:product:1'
    UNTP_TYPES = [
        'DigitalProductPassport',
        'DigitalConformityCredential',
        'DigitalFacilityRecord',
        'DigitalTraceabilityEvent',
    ]

    def setUp(self):
        super().setUp()
        self.issuer = factories.make_did(label='Issuer')
        self.schema = self.untp_schema()

    def untp_schema(self, untp_type='DigitalProductPassport', declared=True):
        """A schema row the form offers, and the document behind it.

        The dropdown filters on the ``type`` column, while ``is_untp`` reads
        the credential types out of the stored document, so the two can be
        made to disagree.
        """
        types = ['VerifiableCredential'] + ([untp_type] if declared else [])
        return Schemas.objects.create(
            file_schema='untp-{}.json'.format(untp_type.lower()),
            type=untp_type,
            data=json.dumps({
                'title': untp_type,
                'name': [{'value': untp_type, 'lang': 'en'}],
                'properties': {'type': {'default': types}},
            }),
        )

    def upload(self, payload):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return SimpleUploadedFile(
            'subject.json', body, content_type='application/json'
        )

    def form(self, subject=None, payload=None, schema=None, **data):
        if payload is None:
            payload = {'credentialSubject': subject if subject is not None
                       else {'id': self.SUBJECT_ID, 'name': 'A product'}}
        fields = {
            'issuer': str(self.issuer.id),
            'schema': str((schema or self.schema).id),
        }
        fields.update(data)
        return UNTPCredentialImportForm(
            data=fields, files={'file_import': self.upload(payload)}
        )

    def issuance(self, answer=(201, {'id': 'urn:uuid:1'})):
        return patch(
            'idhub.admin.forms.CredentialIssuanceService.issue_untp_credential',
            return_value=answer,
        )

    def issue(self, form, answer=(201, {'id': 'urn:uuid:1'})):
        """Hands the validated form to the service and reports what it got."""
        with self.issuance(answer) as service:
            form.save(self.admin_user)
        return service.call_args.kwargs

    # -- the file itself ---------------------------------------------------

    def test_a_file_that_is_not_utf8_is_refused(self):
        form = self.form(payload=b'\xff\xfe{"credentialSubject": {}}')

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['file_import'], [
            'File is not UTF-8 encoded. Please save the file as UTF-8.'
        ])

    def test_a_missing_file_is_reported_before_the_guard_against_it(self):
        # clean_file_import opens with an "if not uploaded_file", which a
        # required FileField can never reach: when the file is absent the
        # field fails first and the method is not called at all.
        form = UNTPCredentialImportForm(data={
            'issuer': str(self.issuer.id), 'schema': str(self.schema.id),
        })

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['file_import'], ['This field is required.'])

        form.cleaned_data = {}
        self.assertIsNone(form.clean_file_import())

    def test_a_document_that_is_not_an_object_is_refused(self):
        form = self.form(payload=[{'credentialSubject': {}}])

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), ['The uploaded file must be a JSON object.'])

    def test_a_document_without_a_credential_subject_is_refused(self):
        form = self.form(payload={'name': 'A product'})

        self.assertFalse(form.is_valid())
        self.assertEqual(
            errors(form),
            ["The uploaded JSON must contain a 'credentialSubject'."],
        )

    def test_a_credential_subject_that_is_neither_object_nor_array_is_refused(self):
        form = self.form(subject='did:web:testserver:product:1')

        self.assertFalse(form.is_valid())
        self.assertEqual(
            errors(form),
            ["'credentialSubject' must be an object or an array of objects."],
        )

    def test_a_subject_without_an_id_needs_a_did_to_be_minted(self):
        form = self.form(subject={'name': 'A product with no id'})

        self.assertFalse(form.is_valid())
        self.assertEqual(
            errors(form), ["The 'credentialSubject' must contain at least one 'id'."]
        )

    def test_minting_a_did_without_saying_how_is_refused(self):
        form = self.form(subject={'name': 'A product'}, create_did='on')

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['did_method'], [
            'This field is required when creating a new DID.'
        ])

    # -- several subjects at once -------------------------------------------

    def test_only_traceability_events_may_carry_several_subjects(self):
        for untp_type in self.UNTP_TYPES:
            with self.subTest(untp_type=untp_type):
                schema = self.schema if untp_type == 'DigitalProductPassport' \
                    else self.untp_schema(untp_type)
                form = self.form(
                    subject=[{'id': self.SUBJECT_ID}], schema=schema
                )

                if untp_type == 'DigitalTraceabilityEvent':
                    self.assertTrue(form.is_valid(), form.errors.as_text())
                else:
                    self.assertFalse(form.is_valid())
                    self.assertEqual(errors(form), [
                        'A list of credential subjects is only supported for '
                        'Digital Traceability Events (DTE).'
                    ])

    def test_one_new_did_cannot_stand_for_several_events(self):
        form = self.form(
            subject=[{'id': self.SUBJECT_ID}, {'id': 'did:web:testserver:product:2'}],
            schema=self.untp_schema('DigitalTraceabilityEvent'),
            create_did='on',
            did_method=str(DID.Types.WEB.value),
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(errors(form), [
            'Cannot assign a single new DID to a credential containing '
            'multiple traceability events. Please upload them individually '
            'or ensure IDs are pre-defined.'
        ])

    def test_a_traceability_event_without_any_id_is_accepted(self):
        # The id is only demanded of the other three types: an event is about
        # something that happened, not about an identity being described.
        form = self.form(
            subject=[{'eventType': 'transform'}],
            schema=self.untp_schema('DigitalTraceabilityEvent'),
        )

        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data['extracted_subject_ids'], [])

    def test_the_first_event_of_a_list_names_the_subject_of_the_credential(self):
        product = DID.objects.create(
            label='Product', type=DID.Types.WEB, is_product=True
        )
        product.set_did()
        product.save()
        form = self.form(
            subject=[{'id': product.did}, {'id': self.SUBJECT_ID}],
            schema=self.untp_schema('DigitalTraceabilityEvent'),
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())

        self.assertEqual(self.issue(form)['subject_did'], product)

    def test_a_subject_id_no_product_identity_answers_for_is_left_unresolved(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors.as_text())

        self.assertIsNone(self.issue(form)['subject_did'])

    # -- what save() hands to the service ----------------------------------

    def test_a_schema_the_document_does_not_declare_untp_is_issued_plain(self):
        # The dropdown goes by the type column and is_untp by the document,
        # so a row where they disagree reaches save() with no untp type: the
        # credential is issued as a bare VerifiableCredential.
        schema = self.untp_schema(declared=False)
        form = self.form(schema=schema)
        self.assertTrue(form.is_valid(), form.errors.as_text())

        self.assertEqual(self.issue(form)['credential_type'],
                         ['VerifiableCredential'])

    def test_a_minted_did_replaces_the_id_of_the_only_subject(self):
        form = self.form(
            subject={'name': 'A product with no id'},
            create_did='on',
            did_method=str(DID.Types.WEB.value),
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())

        kwargs = self.issue(form)
        product = DID.objects.get(is_product=True)
        self.assertEqual(kwargs['subject_did'], product)
        self.assertEqual(kwargs['subject_data']['id'], product.did)

    def test_a_minted_did_would_only_replace_the_first_of_several_events(self):
        # Unreachable: clean() refuses a list and create_did together, so the
        # rewrite save() does for that case is pinned by granting the consent
        # afterwards, which is what a view bypassing validation would do.
        form = self.form(
            subject=[{'id': self.SUBJECT_ID}, {'id': 'did:web:testserver:product:2'}],
            schema=self.untp_schema('DigitalTraceabilityEvent'),
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())
        form.cleaned_data['create_did'] = True
        form.cleaned_data['did_method'] = DID.Types.WEB.value

        subjects = self.issue(form)['subject_data']
        product = DID.objects.get(is_product=True)
        self.assertEqual(
            [subject['id'] for subject in subjects],
            [product.did, 'did:web:testserver:product:2'],
        )

    def test_a_minted_did_has_nothing_to_rewrite_in_a_list_of_strings(self):
        # Same bypass as above, over a list whose items are not objects: an
        # event list only has to be a list for clean() to let it through, so
        # save() checks the shape again before touching anything.
        form = self.form(
            subject=['an event that is only a string'],
            schema=self.untp_schema('DigitalTraceabilityEvent'),
        )
        self.assertTrue(form.is_valid(), form.errors.as_text())
        form.cleaned_data['create_did'] = True
        form.cleaned_data['did_method'] = DID.Types.WEB.value

        kwargs = self.issue(form)
        self.assertEqual(kwargs['subject_data'], ['an event that is only a string'])
        self.assertEqual(kwargs['subject_did'], DID.objects.get(is_product=True))

    def test_a_refused_issuance_is_reported_as_a_non_field_error(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors.as_text())

        with self.issuance((400, {'error': 'bad subject', 'details': 'no name'})):
            with self.assertRaises(ValidationError) as caught:
                form.save(self.admin_user)

        self.assertEqual(
            caught.exception.messages, ['Issuance failed: bad subject no name']
        )
