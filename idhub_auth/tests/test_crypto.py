"""Key derivation and encrypted fields of the User model.

No database is touched: every method under test works on an unsaved
instance, so these run as SimpleTestCase. What they need is the key in the
cache, which is where ``derive_key_from_password`` looks when no password is
given.
"""
import base64

from nacl.exceptions import CryptoError

from django.core.cache import cache
from django.test import SimpleTestCase

from idhub_auth.models import User
from test_support.base import KeyDidsMixin
from test_support.mocks import FastKdfMixin


class UserCryptoTest(FastKdfMixin, KeyDidsMixin, SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.user = User(email='crypto@example.org')
        self.user.set_encrypted_sensitive_data()

    def test_set_salt_is_sixteen_random_bytes(self):
        self.assertEqual(len(self.user.get_salt()), 16)
        self.assertEqual(
            base64.b64encode(self.user.get_salt()).decode(), self.user.salt
        )

        previous = self.user.salt
        self.user.set_salt()
        self.assertNotEqual(self.user.salt, previous)

    def test_derive_key_is_deterministic(self):
        self.assertEqual(
            self.user.derive_key_from_password(b'pass'),
            self.user.derive_key_from_password(b'pass'),
        )
        self.assertEqual(len(self.user.derive_key_from_password(b'pass')), 32)

    def test_derive_key_depends_on_the_salt(self):
        key = self.user.derive_key_from_password(b'pass')
        self.user.set_salt()
        self.assertNotEqual(self.user.derive_key_from_password(b'pass'), key)

    def test_derive_key_falls_back_to_the_cached_key(self):
        # Any falsy password reaches the cache, the empty string included.
        from_cache = self.user.derive_key_from_password()
        self.assertEqual(self.user.derive_key_from_password(''), from_cache)
        self.assertEqual(
            self.user.derive_key_from_password(self.KEY_DIDS.encode()), from_cache
        )

    def test_derive_key_requires_bytes(self):
        with self.assertRaises(TypeError):
            self.user.derive_key_from_password('1234')

    def test_derive_key_without_salt(self):
        with self.assertRaises(ValueError):
            User(email='nosalt@example.org').derive_key_from_password()

    def test_derive_key_without_the_key_in_cache(self):
        cache.delete('KEY_DIDS')
        with self.assertRaises(AttributeError):
            self.user.derive_key_from_password()

    def test_set_encrypted_sensitive_data_also_sets_the_salt(self):
        user = User(email='fresh@example.org')
        self.assertEqual(user.salt, '')

        user.set_encrypted_sensitive_data()
        self.assertEqual(len(user.get_salt()), 16)
        self.assertTrue(user.encrypted_sensitive_data)
        base64.b64decode(user.encrypted_sensitive_data.encode())

    def test_sensitive_data_is_a_random_key(self):
        secret = self.user.decrypt_sensitive_data()
        self.assertEqual(len(base64.b64decode(secret.encode())), 64)
        self.assertEqual(self.user.decrypt_sensitive_data(), secret)

    def test_sensitive_data_is_not_readable_with_another_key(self):
        self.set_key_dids('a different key')
        with self.assertRaises(CryptoError):
            self.user.decrypt_sensitive_data()

    def test_encrypt_data_round_trip(self):
        for data in ('plain', 'ñandú 😀', 'x' * 100000, ''):
            with self.subTest(data=data[:10]):
                self.assertEqual(
                    self.user.decrypt_data(self.user.encrypt_data(data)), data
                )

    def test_encrypt_data_is_not_deterministic(self):
        self.assertNotEqual(
            self.user.encrypt_data('same'), self.user.encrypt_data('same')
        )

    def test_encrypt_data_is_per_user(self):
        encrypted = self.user.encrypt_data('private')
        other = User(email='other@example.org')
        other.set_encrypted_sensitive_data()

        with self.assertRaises(CryptoError):
            other.decrypt_data(encrypted)

    def test_change_password_key_keeps_the_data_readable(self):
        encrypted = self.user.encrypt_data('private')

        self.user.change_password_key(b'new key')
        self.set_key_dids('new key')
        self.assertEqual(self.user.decrypt_data(encrypted), 'private')

    def test_change_password_key_invalidates_the_old_one(self):
        self.user.change_password_key(b'new key')

        with self.assertRaises(CryptoError):
            self.user.decrypt_sensitive_data()

    def test_change_password_key_requires_bytes(self):
        with self.assertRaises(TypeError):
            self.user.change_password_key('new key')

    def test_get_secret_box_round_trip(self):
        box = self.user.get_secret_box(b'pass')
        self.assertEqual(box.decrypt(box.encrypt(b'data')), b'data')
