# Helper routines to manage DIDs/VC/VPs

This module is a wrapper around the functions exported by SpruceID's `DIDKit` framework.

## DID generation and storage

For now DIDs are of the kind `did:key`, with planned support for `did:web` in the near future.

Creation of a DID involves two steps:
* Generate a unique DID controller key
* Derive a `did:key` type from the key

Both must be stored in the IdHub database and linked to a `User` for later retrieval.

```python
# Use case: generate and link a new DID for an existing user
user = request.user # ...

controller_key = idhub_ssikit.generate_did_controller_key()
did_string = idhub_ssikit.keydid_from_controller_key(controller_key)


did = idhub.models.DID(
    did = did_string,
    user = user
)
did_controller_key = idhub.models.DIDControllerKey(
    key_material = controller_key,
    owner_did = did 
)

did.save()
did_controller_key.save()
```

## Verifiable Credential issuance

Verifiable Credential templates are stored as Jinja2 (TBD) templates in `/schemas` folder. Please examine each template to see what data must be passed to it in order to render.

The data passed to the template must at a minimum include:
* issuer_did
* subject_did
* vc_id

For example, in order to render `/schemas/member-credential.json`:

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape
import idhub_ssikit

env = Environment(
    loader=FileSystemLoader("vc_templates"),
    autoescape=select_autoescape()
)
unsigned_vc_template = env.get_template("member-credential.json")

issuer_user = request.user
issuer_did = user.dids[0]  # TODO: Django ORM pseudocode
issuer_did_controller_key = did.keys[0]  # TODO: Django ORM pseudocode

data = {
    "vc_id": "http://pangea.org/credentials/3731",
    "issuer_did": issuer_did,
    "subject_did": "did:web:[...]",
    "issuance_date": "2020-08-19T21:41:50Z",
    "subject_is_member_of": "Pangea"
}
signed_credential = idhub_ssikit.render_and_sign_credential(
    unsigned_vc_template,
    issuer_did_controller_key,
    data
)
```