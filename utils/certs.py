from pyhanko.sign.signers import SimpleSigner
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization
from pyhanko_certvalidator.registry import SimpleCertificateStore
from asn1crypto import x509, keys


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

    key_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    kinfo = keys.PrivateKeyInfo.load(key_der)

    cert_der = cert.public_bytes(serialization.Encoding.DER)
    asn1_cert = x509.Certificate.load(cert_der)

    asn1_other_certs = set()
    if other_certs_pkcs12:
        for extra_cert in other_certs_pkcs12:
            extra_der = extra_cert.public_bytes(serialization.Encoding.DER)
            asn1_other_certs.add(x509.Certificate.load(extra_der))

    cs = SimpleCertificateStore()
    if asn1_other_certs:
        cs.register_multiple(asn1_other_certs)

    return SimpleSigner(
        signing_key=kinfo,
        signing_cert=asn1_cert,
        cert_registry=cs,
        signature_mechanism=None,
        prefer_pss=False,
    )
