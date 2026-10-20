"""Base test cases shared by the view, table and template tests."""
from django.core.cache import cache
from django.test import TestCase, override_settings

from test_support import factories
from test_support.mocks import FastKdfMixin, OfflineHttpMixin


class KeyDidsMixin:
    """Puts the encryption key where the models look for it.

    The key lives in the process-wide cache, so it is restored after each
    test: leaving it set makes the outcome depend on test order.
    """

    KEY_DIDS = '1234'

    def setUp(self):
        super().setUp()
        self.set_key_dids(self.KEY_DIDS)

    def set_key_dids(self, value):
        cache.set('KEY_DIDS', value, None)
        self.addCleanup(cache.delete, 'KEY_DIDS')


@override_settings(
    DOMAIN='testserver',
    ENABLE_EMAIL=False,
    LANGUAGE_CODE='en',
    API_DLT_URL='',
)
class IdHubBaseTestCase(OfflineHttpMixin, FastKdfMixin, KeyDidsMixin, TestCase):
    """Settings isolation plus the encryption key, without any fixture."""


class IdHubTestCase(IdHubBaseTestCase):
    """Adds the main organization, a plain user and an admin."""

    USER_EMAIL = 'normaluser@example.org'
    USER_PASSWORD = 'testpass12'
    ADMIN_EMAIL = 'adminuser@example.org'
    ADMIN_PASSWORD = 'adminpass12'

    def setUp(self):
        super().setUp()
        self.org = factories.make_organization()
        self.user = factories.make_user(self.USER_EMAIL, self.USER_PASSWORD)
        self.admin_user = factories.make_user(
            self.ADMIN_EMAIL, self.ADMIN_PASSWORD, admin=True
        )

    def user_login(self):
        return self.client.login(email=self.USER_EMAIL, password=self.USER_PASSWORD)

    def admin_login(self):
        return self.client.login(email=self.ADMIN_EMAIL, password=self.ADMIN_PASSWORD)
