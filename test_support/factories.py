"""Object builders for the test suite."""
import base64
import json
import os

from pathlib import Path

from django.conf import settings

from idhub.models import DID, Schemas, VerificableCredential
from idhub_auth.models import User
from oidc4vp.models import Organization


def make_user(email, password, admin=False, accept_gdpr=True):
    create = User.objects.create_superuser if admin else User.objects.create_user
    user = create(email=email, password=password)
    if accept_gdpr:
        user.accept_gdpr = True
        user.save()
    return user


def make_organization(name=None, main=True):
    return Organization.objects.create(name=name or settings.DOMAIN, main=main)


def make_did(label='Default', user=None, type=DID.Types.KEY):
    did = DID.objects.create(label=label, type=type.value, user=user)
    did.set_did()
    did.save()
    return did


def read_schema(file_name):
    return Path(settings.SCHEMAS_DIR).joinpath(file_name).read_text()


# The generic DNIe test certificate shipped by the Policia Nacional, already
# in the repo. Common Name "Ficticio Activo, Ciudadano (FIRMA)".
EIDAS1_PFX_NAME = 'signerDNIe004.pfx'
EIDAS1_PFX_PASSWORD = '123456'


def read_eidas1_pfx():
    path = Path(settings.BASE_DIR).joinpath('examples', EIDAS1_PFX_NAME)
    return path.read_bytes()


def make_eidas1_did(label='Organisation certificate', material=None, **kwargs):
    """The row ImportCertificateForm builds: a certificate, not a real DID."""
    did = DID(
        label=label,
        type=DID.Types.KEY,
        did=EIDAS1_PFX_NAME,
        eidas1=True,
        **kwargs,
    )
    did.set_key_material(json.dumps(material if material is not None else {
        'cert': base64.b64encode(read_eidas1_pfx()).decode(),
        'passphrase': EIDAS1_PFX_PASSWORD,
    }))
    did.save()
    return did


def make_schema(file_name):
    data = read_schema(file_name)
    ldata = json.loads(data)
    return Schemas.objects.create(
        file_schema=file_name,
        data=data,
        type=ldata.get('title'),
        _name=json.dumps(ldata.get('name', '')),
        _description=json.dumps(ldata.get('description', '')),
    )


def make_credential(user, schema, issuer_did, csv_data=None, **kwargs):
    """Builds an ENABLED credential the way ImportForm.create_credential does."""
    cred = VerificableCredential(
        verified=False,
        user=user,
        csv_data=json.dumps(csv_data or {}),
        issuer_did=issuer_did,
        schema=schema,
        **kwargs,
    )
    cred.set_type()
    cred.save()
    return cred


MEMBERSHIP_ROW = {
    'organisation': 'Test Org',
    'affiliatedSince': '2024-01-01',
    'typeOfPerson': 'natural',
    'firstName': 'Dummy',
    'email': 'normaluser@example.org',
}


def make_issued_credential(user, file_name='membership-card.json', csv_data=None,
                           domain='https://testserver'):
    """A signed, ISSUED credential: what a holder can actually present."""
    schema = Schemas.objects.filter(file_schema=file_name).first()
    cred = make_credential(
        user,
        schema or make_schema(file_name),
        make_did(label='Issuer'),
        csv_data if csv_data is not None else MEMBERSHIP_ROW,
    )
    cred.issue(make_did(label='Subject', user=user), domain)
    cred.save()
    return cred


def make_presentation(user, credentials, code='the-code'):
    """Signs a verifiable presentation the way AuthorizeForm does.

    Built through the form itself rather than by hand, so the fixture cannot
    drift away from what the project really sends.
    """
    from oidc4vp.forms import AuthorizeForm

    form = AuthorizeForm(
        data={c.type.lower(): str(c.id) for c in credentials},
        user=user,
        org=None,
        code=code,
        presentation_definition=[c.type for c in credentials],
    )
    assert form.is_valid(), form.errors
    form.save(commit=False)
    return form.vp


def make_schemas():
    """Loads every schema shipped in settings.SCHEMAS_DIR."""
    created = []
    for file_name in sorted(os.listdir(settings.SCHEMAS_DIR)):
        if not file_name.endswith('.json'):
            continue
        if Schemas.objects.filter(file_schema=file_name).exists():
            continue
        created.append(make_schema(file_name))
    return created
