from pyhanko.sign.signers import SimpleSigner
from cryptography.hazmat.primitives.serialization import pkcs12
from pyhanko_certvalidator.registry import SimpleCertificateStore
from pyhanko.keys import _translate_pyca_cryptography_cert_to_asn1
from pyhanko.keys import _translate_pyca_cryptography_key_to_asn1


def load_cert(pfx_bytes, passphrase):
    try:
        (
        private_key,
        cert,
        other_certs_pkcs12,
        ) = pkcs12.load_key_and_certificates(pfx_bytes, passphrase)
    except (IOError, ValueError, TypeError) as e:
        # logger.error(
        #     'Could not load key material from PKCS#12 file', exc_info=e
        # )
        return None

    kinfo = _translate_pyca_cryptography_key_to_asn1(private_key)
    cert = _translate_pyca_cryptography_cert_to_asn1(cert)
    other_certs_pkcs12 = set(
        map(_translate_pyca_cryptography_cert_to_asn1, other_certs_pkcs12)
    )

    cs = SimpleCertificateStore()
    certs_to_register = set(other_certs_pkcs12)
    cs.register_multiple(certs_to_register)
    return SimpleSigner(
        signing_key=kinfo,
        signing_cert=cert,
        cert_registry=cs,
        signature_mechanism=None,
        prefer_pss=False,
    )
