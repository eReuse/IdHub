"""Secret generation and encrypted fields of the Organization model.

Organization carries its own copy of the key derivation and encryption code
that lives in User. These tests cover it on its own and pin that both copies
still agree, so extracting a shared mixin stays a safe refactor.
"""
import base64

from nacl.exceptions import CryptoError

from django.core.cache import cache
from django.test import SimpleTestCase

from idhub_auth.models import User
from oidc4vp.models import (
    SALT_CHARS,
    Organization,
    gen_salt,
    set_client_id,
    set_client_secret,
    set_code,
)
from test_support.base import KeyDidsMixin
from test_support.mocks import FastKdfMixin


class GenSaltTest(SimpleTestCase):
    def test_length_and_alphabet(self):
        salt = gen_salt(24)
        self.assertEqual(len(salt), 24)
        self.assertTrue(set(salt) <= set(SALT_CHARS))

    def test_is_random(self):
        self.assertNotEqual(gen_salt(24), gen_salt(24))

    def test_rejects_a_non_positive_length(self):
        for length in (0, -1):
            with self.subTest(length=length):
                with self.assertRaises(ValueError):
                    gen_salt(length)

    def test_field_defaults_match_their_max_length(self):
        for generate, expected in (
            (set_client_id, 24),
            (set_client_secret, 48),
            (set_code, 24),
        ):
            with self.subTest(generate=generate.__name__):
                self.assertEqual(len(generate()), expected)


class OrganizationCryptoTest(FastKdfMixin, KeyDidsMixin, SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.org = Organization(name='Test Org')
        self.org.set_encrypted_sensitive_data()

    def test_set_encrypted_sensitive_data_also_sets_the_salt(self):
        org = Organization(name='Fresh')
        self.assertIsNone(org.salt)

        org.set_encrypted_sensitive_data()
        self.assertEqual(len(org.get_salt()), 16)
        self.assertEqual(len(base64.b64decode(org.decrypt_sensitive_data())), 64)

    def test_derive_key_without_salt(self):
        # get_salt() returns '' instead of failing, but the kdf rejects it
        # anyway, so the guard buys nothing over the User version.
        self.assertEqual(Organization(name='Fresh').get_salt(), '')
        with self.assertRaises(ValueError):
            Organization(name='Fresh').derive_key_from_password()

    def test_derive_key_without_the_key_in_cache(self):
        cache.delete('KEY_DIDS')
        with self.assertRaises(AttributeError):
            self.org.derive_key_from_password()

    def test_encrypt_data_round_trip(self):
        for data in ('plain', 'niño en el camión;', ''):
            with self.subTest(data=data):
                self.assertEqual(
                    self.org.decrypt_data(self.org.encrypt_data(data)), data
                )

    def test_sensitive_data_is_not_readable_with_another_key(self):
        self.set_key_dids('a different key')
        with self.assertRaises(CryptoError):
            self.org.decrypt_sensitive_data()

    def test_change_password_key_keeps_the_data_readable(self):
        encrypted = self.org.encrypt_data('private')

        self.org.change_password_key(b'new key')
        self.set_key_dids('new key')
        self.assertEqual(self.org.decrypt_data(encrypted), 'private')

    def test_change_password_key_invalidates_the_old_one(self):
        self.org.change_password_key(b'new key')

        with self.assertRaises(CryptoError):
            self.org.decrypt_sensitive_data()

    def test_derives_the_same_key_as_user(self):
        user = User(email='same@example.org')
        user.salt = self.org.salt
        self.assertEqual(
            user.derive_key_from_password(), self.org.derive_key_from_password()
        )
