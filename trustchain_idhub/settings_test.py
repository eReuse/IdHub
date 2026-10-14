"""Settings for the Python test suite.

Run with: ./manage.py test --settings=trustchain_idhub.settings_test

Self-contained on purpose: the values below are injected into os.environ
before importing the real settings, so the suite no longer depends on the
developer's .env (decouple reads os.environ first).
"""
import os
import tempfile

_OVERRIDES = {
    'SECRET_KEY': 'test-only-secret-key-not-used-anywhere-else',
    # Must match the host Django's test client sends, so that credentials
    # rendered during tests point their @context at a resolvable URL.
    'DOMAIN': 'testserver',
    # settings.py asserts DOMAIN is in ALLOWED_HOSTS, and the developer's .env
    # lists the real deployment host.
    'ALLOWED_HOSTS': 'testserver',
    'DEBUG': 'False',
    'DEVELOPMENT': 'False',
    'ENABLE_EMAIL': 'False',
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
    'LANGUAGE_CODE': 'en',
    # No DLT: VerificableCredential.call_oracle() must not reach the network.
    'API_DLT_URL': '',
    'SYNC_ORG_DEV': 'n',
    # The oidc4vp flow reads these three, and the developer's .env switches the
    # redirection on: without pinning them the result of a verification
    # depends on who runs the suite.
    'OIDC_REDIRECT': 'False',
    'ALLOW_CODE_URI': 'https://testserver/oidc4vp/allow_code',
    # Spelled the way Schemas.get_type builds it (title case, no spaces), as
    # .env.example does: the holder matches its credentials against this.
    'SUPPORTED_CREDENTIALS': "['MembershipCard']",
    'STATIC_ROOT': tempfile.mkdtemp(prefix='idhub-test-static-'),
    # Keeps uploaded fixtures out of idhub/upload/ in the working tree.
    'MEDIA_ROOT': tempfile.mkdtemp(prefix='idhub-test-media-'),
}
os.environ.update(_OVERRIDES)

from .settings import *  # noqa: E402,F403

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'idhub-test',
    },
}

# Argon2i is the production hasher and dominates the runtime of any test that
# creates users.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Several tests drive a view into a 500 on purpose, to pin down how it reacts to
# malformed input. django.request logs a full traceback for each one, which
# buries the actual test result.
# An empty handler list is not enough: with no handler anywhere in the chain,
# logging falls back to lastResort, which still writes to stderr.
LOGGING = {
    **LOGGING,  # noqa: F405
    'handlers': {
        **LOGGING['handlers'],  # noqa: F405
        'null': {'class': 'logging.NullHandler'},
    },
    'loggers': {
        'django.request': {'handlers': ['null'], 'propagate': False},
    },
}
