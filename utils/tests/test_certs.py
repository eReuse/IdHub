from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from pyhanko.sign.signers import SimpleSigner

from utils import certs


PFX_PATH = Path(settings.BASE_DIR) / 'examples' / 'signerDNIe004.pfx'
PASSPHRASE = b'123456'


class LoadCertTest(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pfx = PFX_PATH.read_bytes()

    def test_loads_signer_with_right_passphrase(self):
        signer = certs.load_cert(self.pfx, PASSPHRASE)
        self.assertIsInstance(signer, SimpleSigner)
        self.assertIsNotNone(signer.signing_key)
        self.assertIsNotNone(signer.signing_cert)

    def test_signing_cert_is_the_test_dnie(self):
        signer = certs.load_cert(self.pfx, PASSPHRASE)
        subject = signer.signing_cert.subject.human_friendly
        self.assertIn('Ficticio Activo', subject)

    def test_cert_registry_holds_only_the_bundled_chain(self):
        # This .pfx ships no intermediate certificates, so the registry ends
        # up empty: load_cert registers other_certs_pkcs12, not the signer's
        # own certificate.
        signer = certs.load_cert(self.pfx, PASSPHRASE)
        self.assertEqual(len(list(signer.cert_registry)), 0)

    def test_returns_none_on_wrong_passphrase(self):
        self.assertIsNone(certs.load_cert(self.pfx, b'wrong'))

    def test_returns_none_on_garbage_bytes(self):
        self.assertIsNone(certs.load_cert(b'not a pkcs12 file', PASSPHRASE))

    def test_returns_none_on_empty_bytes(self):
        self.assertIsNone(certs.load_cert(b'', PASSPHRASE))

    def test_returns_none_when_passphrase_is_str(self):
        # The TypeError raised by cryptography is swallowed: callers rely on
        # getting None back instead of an exception.
        self.assertIsNone(certs.load_cert(self.pfx, '123456'))

    def test_returns_none_when_passphrase_is_none(self):
        self.assertIsNone(certs.load_cert(self.pfx, None))
