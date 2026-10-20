"""Tests for idhub.credential_renderer.generate_universal_template().

The function takes a raw UNTP credential (a plain dict) and returns a single
line of HTML that gets embedded in the credential itself as a
``RenderTemplate2024`` render method (see Credential.generate_enveloped_jwt).
Because the payload is attacker-shaped data pasted into HTML by string
concatenation, the escaping behaviour is the main thing under test here.

Nothing touches the database, so SimpleTestCase is enough.
"""

import re

from django.test import SimpleTestCase


class RendererTestCase(SimpleTestCase):
    def render(self, **raw_vc):
        from idhub.credential_renderer import generate_universal_template
        return generate_universal_template(raw_vc)

    def subject_of(self, markup):
        """Everything after the Subject Payload heading."""
        marker = 'Subject Payload</h2>'
        self.assertIn(marker, markup)
        return markup.split(marker, 1)[1]

    def labels_of(self, markup):
        """The field names rendered for scalar values, in order."""
        return re.findall(r'info-label text-muted">([^<]*)</div>', markup)

    def values_of(self, markup):
        return re.findall(r'info-value fw-bold">([^<]*)</div>', markup)

    def badges_of(self, markup):
        return re.findall(r'badge bg-secondary me-1">([^<]*)</span>', markup)

    def hashes_of(self, markup):
        """The three monospace header boxes: credential id and issuer id."""
        return re.findall(r'hash-value">([^<]*)</div>', markup)


class CredentialIdTest(RendererTestCase):
    def test_the_credential_id_is_shown(self):
        markup = self.render(id='urn:uuid:abc')
        self.assertIn('urn:uuid:abc', self.hashes_of(markup))

    def test_a_missing_credential_id_becomes_not_available(self):
        self.assertEqual(self.hashes_of(self.render())[0], 'N/A')

    def test_a_non_string_credential_id_is_coerced(self):
        self.assertEqual(self.hashes_of(self.render(id=42))[0], '42')


class TypesTest(RendererTestCase):
    def test_every_type_gets_its_own_badge(self):
        markup = self.render(type=['VerifiableCredential', 'DigitalProductPassport'])
        self.assertEqual(
            self.badges_of(markup),
            ['VerifiableCredential', 'DigitalProductPassport'],
        )

    def test_a_bare_string_type_is_wrapped_into_a_single_badge(self):
        self.assertEqual(self.badges_of(self.render(type='DigitalFacilityRecord')),
                         ['DigitalFacilityRecord'])

    def test_a_missing_type_renders_no_badge(self):
        self.assertEqual(self.badges_of(self.render()), [])

    def test_an_empty_type_list_renders_no_badge(self):
        self.assertEqual(self.badges_of(self.render(type=[])), [])


class IssuerTest(RendererTestCase):
    def test_the_issuer_id_is_taken_out_of_the_issuer_object(self):
        markup = self.render(issuer={'id': 'did:web:acme.example', 'name': 'Acme'})
        self.assertIn('did:web:acme.example', self.hashes_of(markup))

    def test_the_issuer_name_is_never_rendered(self):
        """Only the DID reaches the template, so the human-readable name of the
        issuing organization is dropped from the rendered credential."""
        self.assertNotIn('Acme', self.render(issuer={'id': 'did:web:x', 'name': 'Acme'}))

    def test_an_issuer_given_as_a_plain_string_is_used_as_is(self):
        markup = self.render(issuer='did:key:zabc')
        self.assertIn('did:key:zabc', self.hashes_of(markup))

    def test_an_issuer_object_without_an_id_becomes_not_available(self):
        self.assertEqual(self.hashes_of(self.render(issuer={'name': 'Acme'}))[1], 'N/A')

    def test_an_empty_issuer_string_becomes_not_available(self):
        self.assertEqual(self.hashes_of(self.render(issuer=''))[1], 'N/A')

    def test_a_missing_issuer_becomes_not_available(self):
        self.assertEqual(self.hashes_of(self.render())[1], 'N/A')


class ValidFromTest(RendererTestCase):
    def valid_from_of(self, markup):
        return re.search(r'info-value fw-bold">([^<]*)</div></div></div>',
                         self.header_of(markup)).group(1)

    def header_of(self, markup):
        return markup.split('Subject Payload</h2>', 1)[0]

    def test_valid_from_is_shown_when_present(self):
        self.assertEqual(self.valid_from_of(self.render(validFrom='2026-01-01')),
                         '2026-01-01')

    def test_issuance_date_is_the_fallback_of_valid_from(self):
        self.assertEqual(self.valid_from_of(self.render(issuanceDate='2025-12-31')),
                         '2025-12-31')

    def test_an_empty_valid_from_falls_back_to_the_issuance_date(self):
        markup = self.render(validFrom='', issuanceDate='2025-12-31')
        self.assertEqual(self.valid_from_of(markup), '2025-12-31')

    def test_without_any_date_it_becomes_not_available(self):
        self.assertEqual(self.valid_from_of(self.render()), 'N/A')


class SubjectShapeTest(RendererTestCase):
    def test_a_subject_object_is_walked_in_place(self):
        subject = self.subject_of(self.render(credentialSubject={'productName': 'Widget'}))
        self.assertEqual(self.labels_of(subject), ['Product Name'])
        self.assertEqual(self.values_of(subject), ['Widget'])

    def test_each_subject_of_a_list_gets_its_own_card(self):
        subject = self.subject_of(
            self.render(credentialSubject=[{'a': 'one'}, {'b': 'two'}])
        )
        self.assertEqual(subject.count('component-card mb-4'), 2)
        self.assertEqual(self.values_of(subject), ['one', 'two'])

    def test_a_scalar_subject_is_printed_raw(self):
        subject = self.subject_of(self.render(credentialSubject='just-a-string'))
        self.assertIn('<div class="col-12 info-value">just-a-string</div>', subject)

    def test_a_missing_subject_renders_an_empty_payload(self):
        subject = self.subject_of(self.render())
        self.assertEqual(self.labels_of(subject), [])

    def test_an_empty_subject_list_renders_an_empty_payload(self):
        subject = self.subject_of(self.render(credentialSubject=[]))
        self.assertEqual(self.labels_of(subject), [])


class KeyNamingTest(RendererTestCase):
    def test_camel_case_keys_become_title_cased_words(self):
        subject = self.subject_of(
            self.render(credentialSubject={'productImage': 'x', 'dueDiligenceInfo': 'y'})
        )
        self.assertEqual(self.labels_of(subject),
                         ['Product Image', 'Due Diligence Info'])

    def test_acronyms_are_split_letter_by_letter(self):
        """Every capital gets a space in front of it, so UNTP-style acronyms end
        up spelled out, and a key starting with a capital keeps a leading
        space."""
        subject = self.subject_of(self.render(credentialSubject={'IDValue': 'x'}))
        self.assertEqual(self.labels_of(subject), [' I D Value'])

    def test_snake_case_keys_keep_their_underscore(self):
        subject = self.subject_of(self.render(credentialSubject={'batch_number': 'x'}))
        self.assertEqual(self.labels_of(subject), ['Batch_Number'])

    def test_context_type_and_id_are_skipped_at_every_level(self):
        subject = self.subject_of(self.render(credentialSubject={
            '@context': ['https://example.org/ctx'],
            'type': ['DigitalProductPassport'],
            'id': 'urn:product:1',
            'serialNumber': 'SN-1',
            'nested': {'id': 'urn:nested:1', 'type': ['Thing'], 'name': 'inner'},
        }))
        self.assertNotIn('urn:product:1', subject)
        self.assertNotIn('urn:nested:1', subject)
        self.assertNotIn('https://example.org/ctx', subject)
        self.assertEqual(self.labels_of(subject), ['Serial Number', 'Name'])

    def test_the_subject_identifier_never_reaches_the_rendered_credential(self):
        """``id`` is skipped to avoid repeating the credential id, but that also
        hides the identifier of the product the passport is about."""
        markup = self.render(id='urn:uuid:cred',
                             credentialSubject={'id': 'urn:product:serial-1'})
        self.assertNotIn('urn:product:serial-1', markup)


class ValueShapeTest(RendererTestCase):
    def test_a_nested_object_gets_a_heading_and_a_card(self):
        subject = self.subject_of(self.render(credentialSubject={
            'dimensions': {'weightValue': '3'},
        }))
        self.assertIn('bi-box-seam', subject)
        self.assertIn('Dimensions</h4>', subject)
        self.assertIn('component-card', subject)
        self.assertEqual(self.labels_of(subject), ['Weight Value'])

    def test_an_empty_nested_object_still_gets_its_heading(self):
        subject = self.subject_of(self.render(credentialSubject={'dimensions': {}}))
        self.assertIn('Dimensions</h4>', subject)
        self.assertEqual(self.labels_of(subject), [])

    def test_a_list_gets_a_collection_heading(self):
        subject = self.subject_of(self.render(credentialSubject={'materials': []}))
        self.assertIn('bi-collection', subject)
        self.assertIn('Materials</h4>', subject)

    def test_objects_in_a_list_are_separated_by_a_rule_from_the_second_one_on(self):
        subject = self.subject_of(self.render(credentialSubject={
            'materials': [{'name': 'a'}, {'name': 'b'}, {'name': 'c'}],
        }))
        self.assertEqual(subject.count('<hr class="my-3 text-muted">'), 2)
        self.assertEqual(self.values_of(subject), ['a', 'b', 'c'])

    def test_scalars_in_a_list_are_printed_without_a_label(self):
        subject = self.subject_of(self.render(credentialSubject={'tags': ['x', 'y']}))
        self.assertEqual(self.labels_of(subject), [])
        self.assertIn('<div class="col-12 info-value fw-bold">x</div>', subject)
        self.assertIn('<div class="col-12 info-value fw-bold">y</div>', subject)

    def test_lists_may_mix_objects_and_scalars(self):
        subject = self.subject_of(self.render(credentialSubject={
            'mixed': [{'name': 'a'}, 'plain'],
        }))
        self.assertEqual(self.values_of(subject), ['a', 'plain'])
        self.assertNotIn('<hr class="my-3 text-muted">', subject)

    def test_non_string_scalars_are_coerced_with_str(self):
        subject = self.subject_of(self.render(credentialSubject={
            'missing': None, 'count': 0, 'recalled': False,
        }))
        self.assertEqual(self.values_of(subject), ['None', '0', 'False'])

    def test_objects_nest_as_deep_as_the_payload_does(self):
        subject = self.subject_of(self.render(credentialSubject={
            'a': {'b': {'c': {'leafValue': 'deep'}}},
        }))
        self.assertEqual(self.values_of(subject), ['deep'])
        self.assertEqual(subject.count('bi-box-seam'), 3)


class SubjectEscapingTest(RendererTestCase):
    """The subject payload is injected with |safe, so html.escape() in Python is
    the only thing standing between the payload and the browser."""

    def test_markup_in_a_value_is_escaped(self):
        subject = self.subject_of(self.render(credentialSubject={
            'note': '<script>alert(1)</script>',
        }))
        self.assertNotIn('<script>', subject)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', subject)

    def test_quotes_in_a_value_are_escaped(self):
        subject = self.subject_of(self.render(credentialSubject={
            'note': 'a" onmouseover="x',
        }))
        self.assertIn('&quot;', subject)
        self.assertNotIn('onmouseover="x', subject)

    def test_markup_in_a_key_is_escaped(self):
        subject = self.subject_of(self.render(credentialSubject={
            '<img src=x onerror=1>': 'v',
        }))
        self.assertNotIn('<img', subject)
        self.assertIn('&lt;', subject)

    def test_title_casing_mangles_markup_inside_a_key_before_escaping_it(self):
        """str.title() capitalizes after any non-letter, so tag names injected in
        a key come back upper-cased. Harmless, but it means the label shown is
        not what the payload said."""
        subject = self.subject_of(self.render(credentialSubject={'<b>k</b>': 'v'}))
        self.assertEqual(self.labels_of(subject), ['&lt;B&gt;K&lt;/B&gt;'])

    def test_markup_in_a_scalar_list_item_is_escaped(self):
        subject = self.subject_of(self.render(credentialSubject={
            'tags': ['<script>alert(1)</script>'],
        }))
        self.assertNotIn('<script>', subject)
        self.assertIn('&lt;script&gt;', subject)

    def test_markup_nested_several_levels_deep_is_escaped(self):
        subject = self.subject_of(self.render(credentialSubject={
            'a': {'b': [{'c': '<script>deep</script>'}]},
        }))
        self.assertNotIn('<script>', subject)
        self.assertIn('&lt;script&gt;deep&lt;/script&gt;', subject)

    def test_a_type_name_is_escaped_inside_its_badge(self):
        markup = self.render(type=['<script>alert(1)</script>'])
        self.assertNotIn('<script>', markup)
        self.assertEqual(self.badges_of(markup), ['&lt;script&gt;alert(1)&lt;/script&gt;'])


class HeaderEscapingTest(RendererTestCase):
    """The credential id, the issuer id and the date are escaped in Python and
    then escaped again by the Django template, because they are interpolated
    without |safe. They are safe, just unreadable."""

    def test_the_credential_id_is_escaped_twice(self):
        markup = self.render(id='<script>alert(1)</script>')
        self.assertNotIn('<script>', markup)
        self.assertIn('&amp;lt;script&amp;gt;', markup)

    def test_the_issuer_id_is_escaped_twice(self):
        markup = self.render(issuer='<i>who</i>')
        self.assertNotIn('<i>who</i>', markup)
        self.assertIn('&amp;lt;i&amp;gt;who', markup)

    def test_the_date_is_escaped_twice(self):
        markup = self.render(validFrom='<em>soon</em>')
        self.assertNotIn('<em>soon</em>', markup)
        self.assertIn('&amp;lt;em&amp;gt;soon', markup)

    def test_an_ampersand_in_the_credential_id_is_shown_mangled(self):
        """A perfectly ordinary id containing & is displayed as '&amp;'."""
        self.assertIn('&amp;amp;', self.render(id='urn:a&b'))


class WhitespaceSqueezeTest(RendererTestCase):
    """The function strips every newline and every run of four spaces from the
    finished document, which also rewrites the data it just escaped."""

    def test_the_result_is_a_single_line(self):
        self.assertNotIn('\n', self.render(credentialSubject={'a': 'b'}))

    def test_four_consecutive_spaces_are_deleted_from_a_value(self):
        subject = self.subject_of(self.render(credentialSubject={'note': 'x    y'}))
        self.assertEqual(self.values_of(subject), ['xy'])

    def test_newlines_inside_a_value_are_deleted(self):
        subject = self.subject_of(self.render(credentialSubject={'note': 'l1\nl2'}))
        self.assertEqual(self.values_of(subject), ['l1l2'])


class FullCredentialTest(RendererTestCase):
    def test_a_realistic_product_passport_renders_every_section(self):
        markup = self.render(**{
            '@context': ['https://www.w3.org/ns/credentials/v2'],
            'id': 'urn:uuid:11111111-1111-1111-1111-111111111111',
            'type': ['VerifiableCredential', 'DigitalProductPassport'],
            'issuer': {'id': 'did:web:idhub.example', 'name': 'IdHub'},
            'validFrom': '2026-10-19T00:00:00Z',
            'credentialSubject': {
                'id': 'urn:product:1',
                'type': ['Product'],
                'productName': 'Refurbished laptop',
                'dimensions': {'weightValue': '1.4', 'weightUnit': 'KGM'},
                'materialsProvenance': [
                    {'name': 'Aluminium', 'recycledShare': '70'},
                    {'name': 'Plastic', 'recycledShare': '30'},
                ],
                'granularityLevel': 'item',
            },
        })
        self.assertIn('urn:uuid:11111111-1111-1111-1111-111111111111',
                      self.hashes_of(markup))
        self.assertIn('did:web:idhub.example', self.hashes_of(markup))
        self.assertEqual(self.badges_of(markup),
                         ['VerifiableCredential', 'DigitalProductPassport'])
        subject = self.subject_of(markup)
        self.assertEqual(
            self.labels_of(subject),
            ['Product Name', 'Weight Value', 'Weight Unit', 'Name',
             'Recycled Share', 'Name', 'Recycled Share', 'Granularity Level'],
        )
        self.assertEqual(
            self.values_of(subject),
            ['Refurbished laptop', '1.4', 'KGM', 'Aluminium', '70', 'Plastic',
             '30', 'item'],
        )
        self.assertEqual(subject.count('<hr class="my-3 text-muted">'), 1)
