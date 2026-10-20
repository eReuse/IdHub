"""Tests for idhub/forms.py: VerificationForm, and the gate it is.

The form is the door of the public /verify/ portal (PublicVerificationView,
idhub/views.py:246): anybody, logged in or not, can post a file to it. So
clean_file_import() is the only thing between an anonymous upload and
VerificationService, and it is the whole of the untested part of the module.

It validates four things, in this order, and stops at the first one that
fails: size, extension, content type, and -only for .json and .jwt- that the
bytes decode as UTF-8.

The last class goes through the view, because the contract of the form only
makes sense against what the view does with what the form lets through.
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from idhub.forms import VerificationForm


TOO_LARGE = VerificationForm.MAX_UPLOAD_SIZE + 1

# Not valid UTF-8, and the first byte of a BOM, which is what a binary file
# uploaded by mistake usually starts with.
NOT_UTF8 = b'\xff\xfe\x00'


class VerificationFormTestCase(SimpleTestCase):
    def upload(self, name='credential.json', content=b'{}',
               content_type='application/json'):
        return SimpleUploadedFile(name, content, content_type=content_type)

    def form(self, **kwargs):
        return VerificationForm(data={}, files={'file_import': self.upload(**kwargs)})

    def assertAccepted(self, **kwargs):
        form = self.form(**kwargs)
        self.assertTrue(form.is_valid(), form.errors.as_data())
        return form

    def assertRefused(self, message, **kwargs):
        form = self.form(**kwargs)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['file_import'], [message])


class FileIsRequiredTest(VerificationFormTestCase):
    def test_posting_no_file_at_all_is_reported_by_the_field(self):
        form = VerificationForm(data={}, files={})
        self.assertEqual(form.errors['file_import'], ['This field is required.'])

    def test_an_empty_file_is_reported_by_the_field(self):
        self.assertRefused('The submitted file is empty.', content=b'')

    def test_the_empty_file_guard_of_the_cleaner_is_unreachable(self):
        """clean_file_import starts with ``if not file: return file``, but the
        field is required, and Django skips clean_<field> when the field itself
        already failed. Nothing can reach that line."""
        for files in ({}, {'file_import': self.upload(content=b'')}):
            form = VerificationForm(data={}, files=files)
            self.assertFalse(form.is_valid())
            self.assertNotIn('file_import', form.cleaned_data)


class SizeLimitTest(VerificationFormTestCase):
    def test_a_file_over_five_megabytes_is_refused(self):
        self.assertRefused(
            'The file is too large. The maximum allowed size is 5MB.',
            content=b'a' * TOO_LARGE,
        )

    def test_exactly_five_megabytes_is_accepted(self):
        self.assertAccepted(content=b'a' * VerificationForm.MAX_UPLOAD_SIZE)

    def test_the_size_is_checked_before_the_extension(self):
        """A huge .txt is reported as too large, not as the wrong kind of
        file."""
        self.assertRefused(
            'The file is too large. The maximum allowed size is 5MB.',
            name='credential.txt', content=b'a' * TOO_LARGE,
        )


class ExtensionTest(VerificationFormTestCase):
    def test_the_three_documented_extensions_are_accepted(self):
        for name in ('credential.json', 'credential.pdf', 'credential.jwt'):
            with self.subTest(name=name):
                self.assertAccepted(name=name)

    def test_any_other_extension_is_refused(self):
        self.assertRefused(
            'Invalid file extension. Only .json, .pdf and .jwt are allowed.',
            name='credential.txt',
        )

    def test_a_name_without_extension_is_refused(self):
        self.assertRefused(
            'Invalid file extension. Only .json, .pdf and .jwt are allowed.',
            name='credential',
        )

    def test_the_extension_is_matched_case_insensitively(self):
        self.assertAccepted(name='CREDENTIAL.JSON')

    def test_only_the_last_extension_counts(self):
        self.assertAccepted(name='credential.pdf.json')

    def test_a_double_extension_cannot_smuggle_anything_through(self):
        self.assertRefused(
            'Invalid file extension. Only .json, .pdf and .jwt are allowed.',
            name='credential.json.exe',
        )

    def test_the_jsonld_extension_is_not_accepted(self):
        """The widget advertises application/ld+json as a content type, but
        .jsonld is not in ALLOWED_EXTENSIONS, so a JSON-LD credential saved
        under its natural name is turned away."""
        self.assertRefused(
            'Invalid file extension. Only .json, .pdf and .jwt are allowed.',
            name='credential.jsonld', content_type='application/ld+json',
        )


class ContentTypeTest(VerificationFormTestCase):
    UNSUPPORTED = ('Unsupported file format. Please upload a valid JSON, PDF, '
                   'or JWT credential.')

    def test_every_declared_content_type_is_accepted(self):
        for content_type in VerificationForm.ALLOWED_CONTENT_TYPES:
            with self.subTest(content_type=content_type):
                self.assertAccepted(content_type=content_type)

    def test_the_generic_content_types_are_let_through(self):
        """Browsers and curl often send one of these for a file they cannot
        label, so they are accepted and the extension does the deciding."""
        for content_type in ('application/octet-stream', 'text/plain', ''):
            with self.subTest(content_type=content_type):
                self.assertAccepted(content_type=content_type)

    def test_an_unrelated_content_type_is_refused(self):
        self.assertRefused(self.UNSUPPORTED, content_type='image/png')

    def test_a_missing_content_type_is_refused(self):
        """A client that sends no Content-Type for the part leaves it as None,
        and None is not the empty string the generic list allows."""
        self.assertRefused(self.UNSUPPORTED, content_type=None)

    def test_the_extension_is_checked_before_the_content_type(self):
        self.assertRefused(
            'Invalid file extension. Only .json, .pdf and .jwt are allowed.',
            name='credential.png', content_type='image/png',
        )


class Utf8Test(VerificationFormTestCase):
    NOT_TEXT = 'The file is not a valid UTF-8 encoded text file.'

    def test_a_json_file_that_is_not_utf8_is_refused(self):
        self.assertRefused(self.NOT_TEXT, name='credential.json', content=NOT_UTF8)

    def test_a_jwt_file_that_is_not_utf8_is_refused(self):
        self.assertRefused(self.NOT_TEXT, name='credential.jwt',
                           content=NOT_UTF8, content_type='application/jwt')

    def test_non_ascii_text_is_accepted(self):
        self.assertAccepted(content='{"name": "Añil ☃"}'.encode())

    def test_a_pdf_is_not_checked_for_being_text(self):
        """The UTF-8 guard only covers .json and .jwt, which leaves out the one
        extension that is binary by definition. See the view tests below for
        what that costs."""
        self.assertAccepted(name='credential.pdf', content=b'%PDF-1.4\xff\xfe',
                            content_type='application/pdf')

    def test_the_file_is_rewound_after_being_read(self):
        """clean_file_import consumes the file to test the encoding, so it has
        to seek(0) or the view would read an empty string."""
        form = self.assertAccepted(content=b'{"a": 1}')
        self.assertEqual(form.cleaned_data['file_import'].read(), b'{"a": 1}')


class VerificationViewTest(TestCase):
    """What the view does with what the form let through."""

    def post(self, name='credential.json', content=b'{}',
             content_type='application/json'):
        return self.client.post(
            reverse('idhub:verify'),
            {'file_import': SimpleUploadedFile(name, content, content_type=content_type)},
        )

    def test_the_portal_is_public(self):
        self.assertEqual(self.client.get(reverse('idhub:verify')).status_code, 200)

    def test_a_refused_file_is_reported_as_a_failed_validation_step(self):
        response = self.post(name='credential.txt')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid file extension')
        self.assertContains(response, 'File validation')

    def test_a_json_file_reaches_the_verification_service(self):
        response = self.post(content=b'not json at all')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Format parsing')

    def test_uploading_a_pdf_crashes_the_public_portal(self):
        """The form accepts .pdf and application/pdf, and the help text invites
        it, but form_valid() does upload.read().decode('utf-8') and
        VerificationService only knows JSON and bare JWTs. Any real PDF -every
        one of them has binary streams- is an unhandled UnicodeDecodeError on
        an unauthenticated endpoint."""
        with self.assertRaises(UnicodeDecodeError):
            self.post(name='credential.pdf', content=b'%PDF-1.4\xff\xfe',
                      content_type='application/pdf')
