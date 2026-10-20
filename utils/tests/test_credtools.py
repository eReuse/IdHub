import contextlib
import csv
import io
import json
import os
import tempfile
from unittest.mock import patch

import jsonschema
import pandas as pd
import requests
from django.test import SimpleTestCase

from utils import credtools


@contextlib.contextmanager
def quiet():
    """credtools reports through print() on almost every branch."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


SUBJECT_SCHEMA = {
    'type': 'object',
    'properties': {
        'credentialSubject': {
            'type': 'object',
            'properties': {
                'id': {'type': 'string'},
                'firstName': {'type': 'string', 'description': 'El nombre'},
                'born': {'type': 'string', 'format': 'date'},
                'score': {'type': 'integer'},
            },
            'required': ['firstName'],
        },
    },
}

PERSON_SCHEMA = {
    'type': 'object',
    'properties': {
        'a': {'type': 'string'},
        'born': {'type': 'string', 'format': 'date'},
    },
    'required': ['a'],
}


class TempDirMixin:

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def path(self, name):
        return os.path.join(self._tmp.name, name)


class RemoveNullValuesTest(SimpleTestCase):

    def test_mutates_in_place_and_returns_none(self):
        data = {'a': 1, 'b': None}
        self.assertIsNone(credtools._remove_null_values(data))
        self.assertEqual(data, {'a': 1})

    def test_drops_none_and_empty_string(self):
        data = {'a': None, 'b': '', 'c': 'x'}
        credtools._remove_null_values(data)
        self.assertEqual(data, {'c': 'x'})

    def test_keeps_zero_and_false(self):
        # Classic regression: 0 and False are falsy but they are not null.
        data = {'zero': 0, 'false': False, 'empty_list': [], 'empty_dict': {}}
        credtools._remove_null_values(data)
        self.assertEqual(data, {'zero': 0, 'false': False, 'empty_list': [], 'empty_dict': {}})

    def test_does_not_recurse_into_nested_dicts_or_lists(self):
        # Filtering is flat: nested nulls survive.
        data = {'nested': {'a': None, 'b': ''}, 'items': [None, '', 1]}
        credtools._remove_null_values(data)
        self.assertEqual(data, {'nested': {'a': None, 'b': ''}, 'items': [None, '', 1]})

    def test_empty_dict_stays_empty(self):
        data = {}
        credtools._remove_null_values(data)
        self.assertEqual(data, {})


class ValidateSchemaTest(SimpleTestCase):

    def test_accepts_valid_draft202012_schema(self):
        with quiet():
            self.assertTrue(credtools.validate_schema(SUBJECT_SCHEMA))

    def test_empty_schema_is_valid(self):
        # {} accepts any instance: valid as a schema, useless as validation.
        with quiet():
            self.assertTrue(credtools.validate_schema({}))

    def test_boolean_schema_is_valid(self):
        with quiet():
            self.assertTrue(credtools.validate_schema(True))

    def test_rejects_unknown_type(self):
        with quiet():
            self.assertFalse(credtools.validate_schema({'type': 'nope'}))

    def test_rejects_non_object(self):
        with quiet():
            self.assertFalse(credtools.validate_schema('foo'))
            self.assertFalse(credtools.validate_schema(None))
            self.assertFalse(credtools.validate_schema([]))

    def test_real_repo_schemas_are_valid(self):
        # These are the ones going through the assert in ImportSchemaForm.
        for name in ('course-credential.json', 'membership-card.json'):
            with self.subTest(schema=name), open(os.path.join('schemas', name)) as f:
                with quiet():
                    self.assertTrue(credtools.validate_schema(json.load(f)))


class ValidateJsonTest(SimpleTestCase):

    def test_accepts_valid_instance(self):
        with quiet():
            self.assertTrue(credtools.validate_json({'a': 'x'}, PERSON_SCHEMA))

    def test_rejects_wrong_type(self):
        with quiet():
            self.assertFalse(credtools.validate_json({'a': 1}, PERSON_SCHEMA))

    def test_rejects_missing_required(self):
        with quiet():
            self.assertFalse(credtools.validate_json({}, PERSON_SCHEMA))

    def test_format_is_not_checked(self):
        # jsonschema.validate without a format_checker ignores "format":
        # that is why validate_json_format exists.
        with quiet():
            self.assertTrue(credtools.validate_json({'a': 'x', 'born': 'no-fecha'}, PERSON_SCHEMA))

    def test_invalid_schema_propagates_schemaerror(self):
        # Only ValidationError is caught, not SchemaError: a broken schema
        # blows up in the caller instead of returning False.
        with self.assertRaises(jsonschema.exceptions.SchemaError), quiet():
            credtools.validate_json({'a': 'x'}, {'type': 'nope'})


class ValidateJsonFormatTest(SimpleTestCase):

    def test_is_broken_formatchecker_is_not_imported(self):
        # BUG: credtools never imports FormatChecker (the import is commented
        # out at the top of the module), so the function is unusable for any
        # input. Nothing in production calls it, hence it went unnoticed.
        # This test turns red as soon as it is fixed, at which point it should
        # be replaced by the real format cases.
        with self.assertRaises(NameError):
            credtools.validate_json_format({'a': 'x'}, PERSON_SCHEMA)


class CompactJsTest(SimpleTestCase):

    def test_compacts_with_inline_context(self):
        doc = {'http://schema.org/name': [{'@value': 'Bob'}]}
        with quiet():
            compacted = credtools.compact_js(doc, {'name': 'http://schema.org/name'})
        self.assertEqual(
            compacted,
            {'@context': {'name': 'http://schema.org/name'}, 'name': 'Bob'},
        )

    def test_returns_none_on_broken_context(self):
        doc = {'http://schema.org/name': [{'@value': 'Bob'}]}
        with quiet():
            self.assertIsNone(credtools.compact_js(doc, {'@vocab': 5}))


class ValidateContextTest(SimpleTestCase):

    def test_accepts_inline_context(self):
        with quiet():
            self.assertTrue(credtools.validate_context({'@context': {'name': 'http://schema.org/name'}}))

    def test_accepts_context_as_list(self):
        with quiet():
            self.assertTrue(credtools.validate_context({'@context': [{'name': 'http://schema.org/name'}]}))

    def test_missing_context_raises_keyerror(self):
        with self.assertRaises(KeyError):
            credtools.validate_context({})

    def test_accepts_garbage_terms(self):
        # jsonld.expand() over the *value* of @context does not validate the
        # terms: the function returns True even for a made-up IRI or a numeric
        # @vocab. A much weaker check than its name suggests.
        with quiet():
            self.assertTrue(credtools.validate_context({'@context': {'name': 'no-es-un-iri'}}))
            self.assertTrue(credtools.validate_context({'@context': {'@vocab': 5}}))


class DereferenceContextTest(SimpleTestCase):

    def test_missing_context_raises_valueerror(self):
        # The except clause does not catch ValueError, so it escapes (and the
        # return None right after the raise is dead code).
        with self.assertRaises(ValueError):
            credtools.dereference_context({})

    def test_empty_context_raises_valueerror(self):
        with self.assertRaises(ValueError):
            credtools.dereference_context({'@context': []})

    def test_downloads_each_context_url(self):
        body = {'@context': {'name': 'http://schema.org/name'}}
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(body).encode()
        with patch('utils.credtools.requests.get', return_value=response) as get, quiet():
            result = credtools.dereference_context({'@context': ['https://example.org/a.jsonld']})
        get.assert_called_once_with('https://example.org/a.jsonld')
        self.assertEqual(result, [body])

    def test_returns_none_on_http_error(self):
        response = requests.Response()
        response.status_code = 404
        response._content = b'{}'
        with patch('utils.credtools.requests.get', return_value=response), quiet():
            self.assertIsNone(
                credtools.dereference_context({'@context': ['https://example.org/a.jsonld']})
            )

    def test_returns_none_on_timeout(self):
        with patch('utils.credtools.requests.get', side_effect=requests.Timeout), quiet():
            self.assertIsNone(
                credtools.dereference_context({'@context': ['https://example.org/a.jsonld']})
            )

    def test_returns_none_on_malformed_json(self):
        response = requests.Response()
        response.status_code = 200
        response._content = b'no soy json'
        with patch('utils.credtools.requests.get', return_value=response), quiet():
            self.assertIsNone(
                credtools.dereference_context({'@context': ['https://example.org/a.jsonld']})
            )

    def test_context_as_string_iterates_characters(self):
        # A string @context is valid JSON-LD, but here it is iterated
        # character by character and every letter is requested as a URL. It
        # fails inside requests and returns None, dereferencing nothing.
        with patch('utils.credtools.requests.get', side_effect=requests.exceptions.MissingSchema) as get:
            with quiet():
                self.assertIsNone(credtools.dereference_context({'@context': 'https://x/a'}))
        get.assert_called_once_with('h')


class DereferenceContextFileTest(TempDirMixin, SimpleTestCase):

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            credtools.dereference_context_file(self.path('nope.json'))

    def test_corrupt_json_raises(self):
        path = self.path('bad.json')
        with open(path, 'w') as f:
            f.write('{no json')
        with self.assertRaises(json.JSONDecodeError):
            credtools.dereference_context_file(path)


class SchemaToCsvTest(TempDirMixin, SimpleTestCase):

    def test_writes_credentialsubject_headers_in_order(self):
        path = self.path('out.csv')
        with quiet():
            self.assertTrue(credtools.schema_to_csv(SUBJECT_SCHEMA, path))
        with open(path, newline='') as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows, [['id', 'firstName', 'born', 'score']])

    def test_keeps_the_id_column(self):
        # Asymmetry with schema_to_xls_basic, which does filter 'id' out.
        path = self.path('out.csv')
        with quiet():
            credtools.schema_to_csv(SUBJECT_SCHEMA, path)
        with open(path, newline='') as f:
            self.assertIn('id', next(csv.reader(f)))

    def test_schema_without_credentialsubject_writes_empty_header(self):
        # No warning at all: it returns True and leaves a CSV holding a
        # single empty line.
        path = self.path('out.csv')
        with quiet():
            self.assertTrue(credtools.schema_to_csv({'type': 'object'}, path))
        with open(path, newline='') as f:
            self.assertEqual(f.read(), '\r\n')


class SchemaToCsvFileTest(TempDirMixin, SimpleTestCase):

    def test_reads_schema_from_file(self):
        schema_path = self.path('schema.json')
        with open(schema_path, 'w') as f:
            json.dump(SUBJECT_SCHEMA, f)
        csv_path = self.path('out.csv')
        with quiet():
            self.assertTrue(credtools.schema_to_csv_file(schema_path, csv_path))
        with open(csv_path, newline='') as f:
            self.assertEqual(next(csv.reader(f)), ['id', 'firstName', 'born', 'score'])

    def test_missing_file_raises_unboundlocalerror(self):
        # BUG: the except clause wants to report the schema in its message,
        # but json_schema does not exist yet when open() fails. Instead of
        # the documented `return False`, an UnboundLocalError propagates.
        with self.assertRaises(UnboundLocalError):
            credtools.schema_to_csv_file(self.path('nope.json'), self.path('out.csv'))


class SchemaToXlsBasicTest(TempDirMixin, SimpleTestCase):

    def test_writes_headers_without_id(self):
        path = self.path('out.xlsx')
        with quiet():
            self.assertTrue(credtools.schema_to_xls_basic(SUBJECT_SCHEMA, path))
        columns = list(pd.read_excel(path, engine='openpyxl').columns)
        self.assertEqual(columns, ['firstName', 'born', 'score'])

    def test_writes_no_data_rows(self):
        path = self.path('out.xlsx')
        with quiet():
            credtools.schema_to_xls_basic(SUBJECT_SCHEMA, path)
        self.assertTrue(pd.read_excel(path, engine='openpyxl').empty)

    def test_accepts_a_file_like_object(self):
        # TemplateExcelDownloadView passes an io.BytesIO, not a path.
        buffer = io.BytesIO()
        with quiet():
            self.assertTrue(credtools.schema_to_xls_basic(SUBJECT_SCHEMA, buffer))
        self.assertTrue(buffer.getvalue().startswith(b'PK'))


class SchemaToXlsCommentTest(TempDirMixin, SimpleTestCase):
    """The export used by TemplateExcelDownloadView (admin/views.py)."""

    def test_writes_headers_without_id(self):
        path = self.path('out.xlsx')
        with quiet():
            self.assertTrue(credtools.schema_to_xls_comment(SUBJECT_SCHEMA, path))
        columns = list(pd.read_excel(path, engine='openpyxl').columns)
        self.assertEqual(columns, ['firstName', 'born', 'score'])

    def test_requires_a_required_list(self):
        # The `[0]` on the credentialSubject.required matches assumes the
        # schema declares it; without it the export blows up.
        schema = json.loads(json.dumps(SUBJECT_SCHEMA))
        del schema['properties']['credentialSubject']['required']
        with self.assertRaises(IndexError), quiet():
            credtools.schema_to_xls_comment(schema, self.path('out.xlsx'))

    def test_rejects_types_outside_string_date_integer(self):
        # fmts only knows string/date/integer: any other schema type is a
        # KeyError.
        schema = json.loads(json.dumps(SUBJECT_SCHEMA))
        schema['properties']['credentialSubject']['properties']['flag'] = {'type': 'boolean'}
        with self.assertRaises(KeyError), quiet():
            credtools.schema_to_xls_comment(schema, self.path('out.xlsx'))

    def test_exports_every_repo_schema_except_device_snapshot(self):
        # The KeyError above is not theoretical: device-snapshot-v1.json
        # declares "array" properties, which is why TemplateExcelDownloadView
        # answers "You cannot download an excel template of this scheme".
        for name in sorted(os.listdir('schemas')):
            if not name.endswith('.json'):
                continue
            with self.subTest(schema=name), open(os.path.join('schemas', name)) as f:
                schema = json.load(f)
            buffer = io.BytesIO()
            if name == 'device-snapshot-v1.json':
                with self.assertRaises(KeyError), quiet():
                    credtools.schema_to_xls_comment(schema, buffer)
            else:
                with quiet():
                    self.assertTrue(credtools.schema_to_xls_comment(schema, buffer))
                self.assertTrue(buffer.getvalue().startswith(b'PK'))


class CsvToJsonTest(TempDirMixin, SimpleTestCase):

    def write_csv(self, content):
        path = self.path('in.csv')
        with open(path, 'w') as f:
            f.write(content)
        return path

    def run_conversion(self, content, schema=PERSON_SCHEMA):
        out = self.path('out.json')
        with quiet():
            result = credtools.csv_to_json(self.write_csv(content), schema, out)
        with open(out) as f:
            return result, json.load(f)

    def test_converts_rows_dropping_empty_cells(self):
        result, data = self.run_conversion('a,born\nx,2024-01-01\ny,\n')
        self.assertTrue(result)
        self.assertEqual(data, [{'a': 'x', 'born': '2024-01-01'}, {'a': 'y'}])

    def test_header_only_csv_gives_empty_array(self):
        result, data = self.run_conversion('a,born\n')
        self.assertTrue(result)
        self.assertEqual(data, [])

    def test_keeps_columns_absent_from_the_schema(self):
        _, data = self.run_conversion('a,sobra\nx,zzz\n')
        self.assertEqual(data, [{'a': 'x', 'sobra': 'zzz'}])

    def test_invalid_rows_are_written_anyway(self):
        # validate_json is called but its result is discarded: the row
        # missing the required 'a' column still ends up in the JSON. The
        # function does not validate, it only prints.
        _, data = self.run_conversion('a,born\n,2024-01-01\n')
        self.assertEqual(data, [{'born': '2024-01-01'}])

    def test_missing_input_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            credtools.csv_to_json(self.path('nope.csv'), PERSON_SCHEMA, self.path('out.json'))


class CsvToJson2Test(TempDirMixin, SimpleTestCase):

    def convert(self, content):
        path = self.path('in.csv')
        with open(path, 'w') as f:
            f.write(content)
        out = self.path('out.json')
        with quiet():
            result = credtools.csv_to_json2(path, out)
        with open(out) as f:
            return result, json.load(f)

    def test_indexes_rows_by_the_no_column(self):
        result, data = self.convert('No,a\n7,x\n8,y\n')
        self.assertTrue(result)
        self.assertEqual(data, {'7': {'No': '7', 'a': 'x'}, '8': {'No': '8', 'a': 'y'}})

    def test_duplicate_keys_overwrite_silently(self):
        _, data = self.convert('No,a\n7,primero\n7,segundo\n')
        self.assertEqual(data, {'7': {'No': '7', 'a': 'segundo'}})

    def test_requires_a_no_column(self):
        path = self.path('in.csv')
        with open(path, 'w') as f:
            f.write('a\nx\n')
        with self.assertRaises(KeyError):
            credtools.csv_to_json2(path, self.path('out.json'))

    def test_keeps_empty_cells(self):
        # Unlike csv_to_json, _remove_null_values is not called here.
        _, data = self.convert('No,a\n7,\n')
        self.assertEqual(data, {'7': {'No': '7', 'a': ''}})


class ValidateSchemaFileTest(TempDirMixin, SimpleTestCase):

    def test_accepts_a_valid_schema_file(self):
        with quiet():
            self.assertTrue(credtools.validate_schema_file('schemas/course-credential.json'))

    def test_returns_true_even_when_the_schema_is_invalid(self):
        # BUG: the return value of validate_schema is never looked at, so
        # this answers True for any file that parses as JSON.
        path = self.path('bad.json')
        with open(path, 'w') as f:
            json.dump({'type': 'nope'}, f)
        with quiet():
            self.assertTrue(credtools.validate_schema_file(path))

    def test_missing_file_raises_unboundlocalerror(self):
        # Same bug as schema_to_csv_file: the except message uses
        # json_schema before it exists.
        with self.assertRaises(UnboundLocalError):
            credtools.validate_schema_file(self.path('nope.json'))

    def test_corrupt_json_raises_unboundlocalerror(self):
        path = self.path('bad.json')
        with open(path, 'w') as f:
            f.write('{no json')
        with self.assertRaises(UnboundLocalError):
            credtools.validate_schema_file(path)


class ValidateJsonFileTest(TempDirMixin, SimpleTestCase):

    def write(self, name, content):
        path = self.path(name)
        with open(path, 'w') as f:
            json.dump(content, f)
        return path

    def test_returns_true_for_a_valid_pair(self):
        data = self.write('data.json', {'a': 'x'})
        schema = self.write('schema.json', PERSON_SCHEMA)
        with quiet():
            self.assertTrue(credtools.validate_json_file(data, schema))

    def test_returns_true_even_when_the_data_is_invalid(self):
        # BUG: like validate_schema_file, it discards the result of
        # validate_json. It only reports loading errors.
        data = self.write('data.json', {})
        schema = self.write('schema.json', PERSON_SCHEMA)
        with quiet():
            self.assertTrue(credtools.validate_json_file(data, schema))

    def test_returns_false_when_a_file_is_missing(self):
        schema = self.write('schema.json', PERSON_SCHEMA)
        with quiet():
            self.assertFalse(credtools.validate_json_file(self.path('nope.json'), schema))
