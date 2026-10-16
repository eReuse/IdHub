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
from unittest.mock import patch

import requests

from openpyxl import Workbook, load_workbook
from openpyxl.packaging.custom import StringProperty

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from idhub.admin.forms import (
    DIDForm,
    EncryptionKeyForm,
    ImportForm,
    ImportSchemaForm,
    ImportSchemaUrlForm,
    MembershipForm,
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

    def test_saving_does_not_create_a_second_default_did(self):
        existing = factories.make_did()
        form = self.form(key=self.KEY_DIDS)
        form.is_valid()
        form.save()
        self.addCleanup(cache.delete, 'KEY_DIDS')

        self.assertEqual([d.pk for d in DID.objects.all()], [existing.pk])


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
