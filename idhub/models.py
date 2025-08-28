import os
import json
import ujson
import pytz
import hashlib
import logging
import datetime
import requests
from collections import OrderedDict
from urllib.parse import urljoin
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from pyvckit.did import (
    generate_keys,
    generate_did,
    gen_did_document,
)
from pyvckit.sign import sign
from pyvckit.verify import verify_signature, verify_schema

from oidc4vp.models import Organization
from idhub_auth.models import User


logger = logging.getLogger(__name__)


# terms protected by https://www.w3.org/2018/credentials/v1
TERMS_PROTECTED = [
    'id',
    'type',
    'VerifiableCredential',
    'VerifiablePresenture2019',
    'EcdsaSecp256r1Signature2019',
    'Ed25519Signature2018',
    'RsaSignature2018',
    'proof'
]


class Event(models.Model):
    class Types(models.IntegerChoices):
        EV_USR_REGISTERED = 1, "User registered"
        EV_USR_WELCOME = 2, "User welcomed"
        EV_DATA_UPDATE_REQUESTED_BY_USER = 3, "Data update requested by user"
        EV_DATA_UPDATE_REQUESTED = 4, "Data update requested. Pending approval by administrator"
        EV_USR_UPDATED_BY_ADMIN = 5, "User's data updated by admin"
        EV_USR_UPDATED = 6, "Your data updated by admin"
        EV_USR_DELETED_BY_ADMIN = 7, "User deactivated by admin"
        EV_DID_CREATED_BY_USER = 8, "DID created by user"
        EV_DID_CREATED = 9, "DID created"
        EV_DID_DELETED = 10, "DID deleted"
        EV_CREDENTIAL_DELETED_BY_USER = 11, "Credential deleted by user"
        EV_CREDENTIAL_DELETED_BY_ADMIN = 12, "Credential deleted by admin"
        EV_CREDENTIAL_DELETED = 13, "Credential deleted"
        EV_CREDENTIAL_ISSUED_FOR_USER = 14, "Credential issued for user"
        EV_CREDENTIAL_ISSUED = 15, "Credential issued"
        EV_CREDENTIAL_PRESENTED_BY_USER = 16, "Credential presented by user"
        EV_CREDENTIAL_PRESENTED = 17, "Credential presented"
        EV_CREDENTIAL_ENABLED = 18, "Credential enabled"
        EV_CREDENTIAL_CAN_BE_REQUESTED = 19, "Credential enabled"
        EV_CREDENTIAL_REVOKED_BY_ADMIN = 20, "Credential revoked by admin"
        EV_CREDENTIAL_REVOKED = 21, "Credential revoked"
        EV_ROLE_CREATED_BY_ADMIN = 22, "Role created by admin"
        EV_ROLE_MODIFIED_BY_ADMIN = 23, "Role modified by admin"
        EV_ROLE_DELETED_BY_ADMIN = 24, "Role deleted by admin"
        EV_SERVICE_CREATED_BY_ADMIN = 25, "Service created by admin"
        EV_SERVICE_MODIFIED_BY_ADMIN = 26, "Service modified by admin"
        EV_SERVICE_DELETED_BY_ADMIN = 27, "Service deleted by admin"
        EV_ORG_DID_CREATED_BY_ADMIN = 28, "Organisational DID created by admin"
        EV_ORG_DID_DELETED_BY_ADMIN = 29, "Organisational DID deleted by admin"
        EV_USR_DEACTIVATED_BY_ADMIN = 30, "User deactivated"
        EV_USR_ACTIVATED_BY_ADMIN = 31, "User activated"
        EV_USR_SEND_VP = 32, "User send Verificable Presentation"
        EV_USR_SEND_CREDENTIAL = 33, "User send credential"
        EV_SCHEME_UPLOAD = 34, "Upload new Schema"
        EV_USR_CRED_TO_DLT = 35, "User presented a credential to DLT"

    created = models.DateTimeField(_("Date"), auto_now=True)
    message = models.CharField(_("Description"), max_length=350)
    type = models.PositiveSmallIntegerField(
        _("Event"),
        choices=Types.choices,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
    )

    def get_type_name(self):
        return self.Types(self.type).label

    @classmethod
    def set_EV_USR_REGISTERED(cls, user):
        msg = _("The user {username} was registered: name: {first_name}, last name: {last_name}").format(
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        cls.objects.create(
            type=cls.Types.EV_USR_REGISTERED,
            message=msg
        )

    @classmethod
    def set_EV_USR_WELCOME(cls, user):
        msg = _("Welcome. You has been registered: name: {first_name}, last name: {last_name}").format(
            first_name=user.first_name,
            last_name=user.last_name
        )
        cls.objects.create(
            type=cls.Types.EV_USR_WELCOME,
            message=msg,
            user=user
        )

    # Is required?
    @classmethod
    def set_EV_DATA_UPDATE_REQUESTED_BY_USER(cls, user):
        msg = _("The user '{username}' has request the update of the following information: ")
        msg += "['field1':'value1', 'field2':'value2'>,...]"
        msg = msg.format(username=user.username)
        cls.objects.create(
            type=cls.Types.EV_DATA_UPDATE_REQUESTED_BY_USER,
            message=msg,
        )

    # Is required?
    @classmethod
    def set_EV_DATA_UPDATE_REQUESTED(cls, user):
        msg = _("You have requested the update of the following information: ")
        msg += "['field1':'value1', 'field2':'value2'>,...]"
        cls.objects.create(
            type=cls.Types.EV_DATA_UPDATE_REQUESTED,
            message=msg,
            user=user
        )

    @classmethod
    def set_EV_USR_UPDATED_BY_ADMIN(cls, user):
        msg = "The admin has updated the following user 's information: "
        msg += "name: {first_name}, last name: {last_name}"
        msg = _(msg).format(
            first_name=user.first_name,
            last_name=user.last_name
        )
        cls.objects.create(
            type=cls.Types.EV_USR_UPDATED_BY_ADMIN,
            message=msg
        )

    @classmethod
    def set_EV_USR_UPDATED(cls, user):
        msg = "The admin has updated your personal information: "
        msg += "name: {first_name}, last name: {last_name}"
        msg = _(msg).format(
            first_name=user.first_name,
            last_name=user.last_name
        )
        cls.objects.create(
            type=cls.Types.EV_USR_UPDATED,
            message=msg,
            user=user
        )

    @classmethod
    def set_EV_USR_DELETED_BY_ADMIN(cls, user):
        msg = _("The admin has deleted the user: username: {username}").format(
            username=user.username,
        )
        cls.objects.create(
            type=cls.Types.EV_USR_DELETED_BY_ADMIN,
            message=msg
        )

    @classmethod
    def set_EV_DID_CREATED_BY_USER(cls, did):
        msg = _("New DID with DID-ID: '{did}' created by user '{username}'").format(
            did=did.did,
            username=did.user.username
        )
        cls.objects.create(
            type=cls.Types.EV_DID_CREATED_BY_USER,
            message=msg,
        )

    @classmethod
    def set_EV_DID_CREATED(cls, did):
        msg = _("New DID with label: '{label}' and DID-ID: '{did}' was created'").format(
            label=did.label,
            did=did.did
        )
        cls.objects.create(
            type=cls.Types.EV_DID_CREATED,
            message=msg,
            user=did.user
        )

    @classmethod
    def set_EV_DID_DELETED(cls, did):
        msg = _("The DID with label '{label}' and DID-ID: '{did}' was deleted from your wallet").format(
            label=did.label,
            did=did.did
        )
        cls.objects.create(
            type=cls.Types.EV_DID_DELETED,
            message=msg,
            user=did.user
        )

    @classmethod
    def set_EV_CREDENTIAL_DELETED_BY_ADMIN(cls, cred):
        msg = _("The credential of type '{type}' and ID: '{id}' was deleted").format(
            type=cred.type,
            id=cred.id,
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_DELETED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_CREDENTIAL_DELETED(cls, cred):
        msg = _("The credential of type '{type}' and ID: '{id}' was deleted from your wallet").format(
            type=cred.type,
            id=cred.id
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_DELETED,
            message=msg,
            user=cred.user
        )

    @classmethod
    def set_EV_CREDENTIAL_ISSUED_FOR_USER(cls, cred):
        msg = _("The credential of type '{type}' and ID: '{id}' was issued for user {username}").format(
            type=cred.type,
            id=cred.id,
            username=cred.user.username
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_ISSUED_FOR_USER,
            message=msg,
        )

    @classmethod
    def set_EV_CREDENTIAL_ISSUED(cls, cred):
        msg = _("The credential of type '{type}' and ID: '{id}' was issued and stored in your wallet").format(
            type=cred.type,
            id=cred.id
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_ISSUED,
            message=msg,
            user=cred.user
        )

    @classmethod
    def set_EV_CREDENTIAL_PRESENTED_BY_USER(cls, cred, verifier):
        msg = "The credential of type '{type}' and ID: '{id}' "
        msg += "was presented by user {username} to verifier '{verifier}"
        msg = _(msg).format(
            type=cred.type,
            id=cred.id,
            username=cred.user.username,
            verifier=verifier
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_PRESENTED_BY_USER,
            message=msg,
        )

    @classmethod
    def set_EV_CREDENTIAL_PRESENTED(cls, cred, verifier):
        msg = "The credential of type '{type}' and ID: '{id}' "
        msg += "was presented to verifier '{verifier}'"
        msg = _(msg).format(
            type=cred.type,
            id=cred.id,
            verifier=verifier
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_PRESENTED,
            message=msg,
            user=cred.user
        )

    @classmethod
    def set_EV_CREDENTIAL_ENABLED(cls, cred):
        msg = _("The credential of type '{type}' was enabled for user {username}").format(
            type=cred.type,
            username=cred.user.username
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_ENABLED,
            message=msg,
        )

    @classmethod
    def set_EV_CREDENTIAL_CAN_BE_REQUESTED(cls, cred):
        msg = _("You can request the '{type}' credential").format(
            type=cred.type
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_CAN_BE_REQUESTED,
            message=msg,
            user=cred.user
        )

    @classmethod
    def set_EV_CREDENTIAL_REVOKED_BY_ADMIN(cls, cred):
        msg = _("The credential of type '{type}' and ID: '{id}' was revoked for ").format(
            type=cred.type,
            id=cred.id
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_REVOKED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_CREDENTIAL_REVOKED(cls, cred):
        msg = _("The credential of type '{type}' and ID: '{id}' was revoked by admin").format(
            type=cred.type,
            id=cred.id
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_REVOKED,
            message=msg,
            user=cred.user
        )

    @classmethod
    def set_EV_ROLE_CREATED_BY_ADMIN(cls):
        msg = _('A new role was created by admin')
        cls.objects.create(
            type=cls.Types.EV_ROLE_CREATED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_ROLE_MODIFIED_BY_ADMIN(cls):
        msg = _('The role was modified by admin')
        cls.objects.create(
            type=cls.Types.EV_ROLE_MODIFIED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_ROLE_DELETED_BY_ADMIN(cls):
        msg = _('The role was removed by admin')
        cls.objects.create(
            type=cls.Types.EV_ROLE_DELETED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_SERVICE_CREATED_BY_ADMIN(cls):
        msg = _('A new service was created by admin')
        cls.objects.create(
            type=cls.Types.EV_SERVICE_CREATED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_SERVICE_MODIFIED_BY_ADMIN(cls):
        msg = _('The service was modified by admin')
        cls.objects.create(
            type=cls.Types.EV_SERVICE_MODIFIED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_SERVICE_DELETED_BY_ADMIN(cls):
        msg = _('The service was removed by admin')
        cls.objects.create(
            type=cls.Types.EV_SERVICE_DELETED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_ORG_DID_CREATED_BY_ADMIN(cls, did):
        msg = _("New Organisational DID with label: '{label}' and DID-ID: '{did}' was created").format(
            label=did.label,
            did=did.did
        )
        cls.objects.create(
            type=cls.Types.EV_ORG_DID_CREATED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_ORG_DID_DELETED_BY_ADMIN(cls, did):
        msg = _("Organisational DID with label: '{label}' and DID-ID: '{did}' was removed").format(
            label=did.label,
            did=did.did
        )
        cls.objects.create(
            type=cls.Types.EV_ORG_DID_DELETED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_USR_DEACTIVATED_BY_ADMIN(cls, user):
        msg = "The user '{username}' was temporarily deactivated: "
        msg += "[name:'{first_name}', last name:'{last_name}']"
        msg = _(msg).format(
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        cls.objects.create(
            type=cls.Types.EV_USR_DEACTIVATED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_USR_ACTIVATED_BY_ADMIN(cls, user):
        msg = "The user '{username}' was activated: "
        msg += "name:'{first_name}', last name:'{last_name}']"
        msg = _(msg).format(
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        cls.objects.create(
            type=cls.Types.EV_USR_ACTIVATED_BY_ADMIN,
            message=msg,
        )

    @classmethod
    def set_EV_USR_SEND_VP(cls, msg, user):
        cls.objects.create(
            type=cls.Types.EV_USR_SEND_VP,
            message=msg,
            user=user
        )

    @classmethod
    def set_EV_USR_SEND_CREDENTIAL(cls, msg):
        cls.objects.create(
            type=cls.Types.EV_USR_SEND_CREDENTIAL,
            message=msg,
        )

    @classmethod
    def set_EV_SCHEME_UPLOAD(cls, msg):
        cls.objects.create(
            type=cls.Types.EV_SCHEME_UPLOAD,
        )

    @classmethod
    def set_EV_USR_CRED_TO_DLT(cls, msg):
        cls.objects.create(
            type=cls.Types.EV_USR_CRED_TO_DLT,
            message=msg,
        )


class DID(models.Model):
    class Types(models.IntegerChoices):
        WEB = 1, "Web"
        KEY = 2, "Key"
        WEBETH = 3, "Web+Ether"

    type = models.PositiveSmallIntegerField(
        _("Type"),
        choices=Types.choices,
    )
    created_at = models.DateTimeField(auto_now=True)
    label = models.CharField(_("Label"), max_length=50)
    did = models.CharField(max_length=250)
    # In JWK format. Must be stored as-is and passed whole to library functions.
    # Example key material:
    # '{"kty":"OKP","crv":"Ed25519","x":"oB2cPGFx5FX4dtS1Rtep8ac6B__61HAP_RtSzJdPxqs","d":"OJw80T1CtcqV0hUcZdcI-vYNBN1dlubrLaJa0_se_gU"}'
    key_material = models.TextField()
    eidas1 = models.BooleanField(default=False)
    is_product = models.BooleanField(default=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dids',
        null=True,
    )
    # JSON-serialized DID document
    didweb_document = models.TextField()
    available = models.BooleanField(default=True)

    def check_remote_did(self):
        if self.get_type() != self.Types.WEB:
            return True

        sdid = self.did[8:].split(":")
        if len(sdid) > 2:
            url = "://{}/did.json".format("/".join(sdid))
        elif len(sdid) == 2:
            url = "://{}/.well-known/{}/did.json".format(*sdid)
        try:
            try:
                verify = not settings.DEBUG
                response = requests.get("https"+url, verify=verify)
            except Exception:
                response = requests.get("http"+url)

            if 200 <= response.status_code < 300:
                return response.text == self.didweb_document
        except Exception:
            return False

        return False

    @property
    def is_organization_did(self):
        if not self.user:
            return True
        return False

    @property
    def is_web(self):
      typ = self.Types(self.type)
      return typ in [self.Types.WEB, self.Types.WEBETH]

    def get_key_material(self):
        user = self.user or self.get_organization()
        return user.decrypt_data(self.key_material)

    def set_key_material(self, value):
        user = self.user or self.get_organization()
        if not user.encrypted_sensitive_data:
            user.set_encrypted_sensitive_data()
            user.save()
        self.key_material = user.encrypt_data(value)

    def set_did(self, new_key_material=None):
        if not new_key_material:
            new_key_material = generate_keys()

        if self.type == self.Types.KEY:
            self.did = generate_did(new_key_material)
        elif self.is_web:
            url = "https://{}".format(settings.DOMAIN)
            path = reverse("idhub:serve_did", args=["a"])

            if path and ".well-known" not in path:
                path = path.split("/a/did.json")[0]
                url = "https://{}/{}".format(settings.DOMAIN, path)

            if self.type == self.Types.WEBETH:
                register_user_url = f"{settings.API_DLT_URL}/registerUser"
                ether_data = requests.post(register_user_url).json()
                err_token = 'api_token has invalid length'
                err_eth = 'eth_pub_key has invalid length'
                assert len(ether_data['data']['api_token']) == 80, err_token
                assert len(ether_data['data']['eth_pub_key']) == 42, err_eth

                # TODO this is always the same, should be on DLT_INIT
                ether_tao_url = f"{settings.API_DLT_URL}/getTa"
                ether_tao_data = requests.get(ether_tao_url).json()

                ether_chainid_url = f"{settings.API_DLT_URL}/getChainId"
                ether_chainid_data = requests.get(ether_chainid_url).json()

                # convert new_key_material to json to add more elements
                new_key_material_json = json.loads(new_key_material)
                new_key_material_json['eth_api_token'] = ether_data['data']['api_token']
                new_key_material_json['eth_subject_pub_key'] = ether_data['data']['eth_pub_key']
                new_key_material_json['eth_issuer_pub_key'] = ether_tao_data['data']['root_pub_key']
                new_key_material_json['eth_chainid'] = ether_chainid_data['data']['chain_id']
                new_key_material = json.dumps(new_key_material_json)

            did = generate_did(new_key_material, url)
            self.did = ":".join(did.split(":")[0:-1]) + ":" + did[-6:]
            key = json.loads(new_key_material)
            url, self.didweb_document = gen_did_document(self.did, key)

        self.set_key_material(new_key_material)

    def get_did_document(self):
        key = json.loads(self.get_key_material())
        url, self.didweb_document = gen_did_document(self.did, key)

    def get_key(self):
        return json.loads(self.key_material)

    def get_organization(self):
        return Organization.objects.get(main=True)

    def get_path(self):
        if settings.DOMAIN == self.did.split(":")[2]:
            did_id = self.did.split(':')[-1]
            if "registry" in self.did:
                return reverse("idhub:serve_registry_did", args=[did_id])
            return reverse("idhub:serve_did", args=[did_id])

        sdid = self.did[8:].split(":")
        if len(sdid) == 2:
            return "https://{}/.well-known/{}/did.json".format(*sdid)

        return "https://{}/did.json".format("/".join(sdid))

    def has_link(self):
        linked_types = [self.Types.WEB, self.Types.WEBETH]
        if self.get_type() in linked_types:
            return True
        return False

    def get_type(self):
        return self.Types(self.type)

    def __str__(self):
        return self.did


class Context(models.Model):
    """
    This context is linked to a schema and is not uploaded when upload a schema.
    Then is autogenerated from the schema
    """
    key = models.CharField(max_length=250, unique=True)

    @classmethod
    def get_context(cls, domain="https://idhub.pangea.org"):
        path = urljoin(domain, "/context/#{}")
        terms = {}
        ctx = {"@context": terms}

        for k in cls.objects.all():
            terms[k.key] = path.format(k.key)

        return json.dumps(ctx)


class SchemaManager(models.Manager):

    def create(self, **kwargs):
        instancia = super().create(**kwargs)

        if instancia.context:
            return instancia

        for c in instancia.get_schema.get("allOf", []):
            sch_subj = c.get("properties", {}).get("credentialSubject", {})
            if sch_subj:
                for k in sch_subj.get("properties", {}).keys():
                    if k in TERMS_PROTECTED or Context.objects.filter(key=k).exists():
                        continue
                    Context.objects.create(key=k)

        return instancia


class Schemas(models.Model):
    type = models.CharField(max_length=250)
    file_schema = models.CharField(_('Schema'), max_length=250)
    data = models.TextField()
    created_at = models.DateTimeField(_("Date"), auto_now=True)
    _name = models.TextField(_("Name"), null=True, db_column='name')
    _description = models.CharField(_("Description"), max_length=250, null=True, db_column='description')
    template_description = models.TextField(null=True)
    context = models.CharField(_('Context'), null=True, max_length=250)

    objects = SchemaManager()

    @property
    def get_schema(self):
        if not self.data:
            return {}
        return json.loads(self.data)

    def _update_and_get_field(self, field_attr, schema_key, is_json=False):
        field_value = getattr(self, field_attr)
        if not field_value:
            field_value = self.get_schema.get(schema_key, [] if is_json else '')
            self._update_model_field(field_attr, field_value)
        try:
            if is_json:
                return json.loads(field_value)
        except Exception:
            pass

        return field_value

    def _update_model_field(self, field_attr, field_value):
        if field_value:
            setattr(self, field_attr, field_value)
            self.save(update_fields=[field_attr])

    @property
    def url(self):
        sh = self.get_schema
        return sh.get("$id", "")

    @property
    def get_type(self):
        sh = self.get_schema
        return sh.get("title", "").title().replace(" ", "")

    @property
    def name(self, request=None):
        names = self._update_and_get_field('_name', 'name',
                                           is_json=True)
        language_code = self._get_language_code(request)
        name = self._get_name_by_language(names, language_code)

        return name

    @property
    def has_credentials(self):
        return self.vcredentials.filter(
            status=VerificableCredential.Status.ISSUED).exists()

    def _get_language_code(self, request=None):
        language_code = settings.LANGUAGE_CODE
        if request:
            language_code = request.LANGUAGE_CODE
        if self._is_catalan_code(language_code):
            language_code = 'ca_ES'

        return language_code

    def _get_name_by_language(self, names, lang_code):
        first = {}
        for name in names:
            first = name
            if name.get('lang') == lang_code:
                return name.get('value', "")

        return first.get("value", "")

    def _is_catalan_code(self, language_code):
        return language_code == 'ca'

    @name.setter
    def name(self, value):
        self._name = json.dumps(value)

    @property
    def description(self):
        return self._update_and_get_field('_description', 'description')

    @description.setter
    def description(self, value):
        self._description = value

    def get_credential_subject_schema(self):
        sc = self.get_data()
        properties = sc["allOf"][1]["properties"]["credentialSubject"]["properties"]
        required = sc["allOf"][1]["properties"]["credentialSubject"]["required"]

        if "id" in required:
            required.remove("id")

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False
        }

        return schema

    def get_data(self):
        return json.loads(self.data)

    def __str__(self):
        return self.file_schema


class ContextFile(models.Model):
    """
    This context is linked to a schema and is uploaded when upload a schema
    """
    data = models.TextField(max_length=250)
    file_name = models.CharField(max_length=250, unique=True)
    schema = models.ForeignKey(
        Schemas,
        on_delete=models.CASCADE,
        related_name='context_file',
    )


class VCTemplate(models.Model):
    wkit_template_id = models.CharField(max_length=250)
    data = models.TextField()


class VCTemplatePdf(models.Model):
    name = models.CharField(_("Name"), max_length=250, unique=True)
    data = models.FileField(upload_to='pdftemplate/')


class VerificableCredential(models.Model):
    """
        Definition of Verificable Credentials
    """
    class Status(models.IntegerChoices):
        ENABLED = 1, _("Enabled")
        ISSUED = 2, _("Issued")
        REVOKED = 3, _("Revoked")
        EXPIRED = 4, _("Expired")

    type = models.CharField(_("Type"), max_length=250)
    id_string = models.CharField(max_length=250)
    verified = models.BooleanField()
    created_on = models.DateTimeField(auto_now=True)
    issued_on = models.DateTimeField(_("Issued on"), null=True)
    data = models.TextField()
    csv_data = models.TextField()
    json_data = models.JSONField(null=False, default=dict)
    hash = models.CharField(max_length=260)
    subject_id = models.CharField(max_length=250, null=True)
    status = models.PositiveSmallIntegerField(
        _("Status"),
        choices=Status.choices,
        default=Status.ENABLED
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vcredentials',
        verbose_name=_("User")
    )
    subject_did = models.ForeignKey(
        DID,
        on_delete=models.CASCADE,
        related_name='subject_credentials',
        null=True
    )
    issuer_did = models.ForeignKey(
        DID,
        on_delete=models.CASCADE,
        related_name='vcredentials',
    )
    eidas1_did = models.ForeignKey(
        DID,
        on_delete=models.CASCADE,
        null=True
    )
    template_pdf = models.ForeignKey(
        VCTemplatePdf,
        on_delete=models.CASCADE,
        null=True
    )
    schema = models.ForeignKey(
        Schemas,
        on_delete=models.CASCADE,
        related_name='vcredentials',
    )
    # revocationBitmapIndex = models.AutoField()

    @property
    def is_didweb(self):
        if self.issuer_did.type == DID.Types.WEB.value:
            return True
        return False

    def get_data(self):
        if not self.data:
            return ""

        return self.user.decrypt_data(self.data)

    def set_data(self, value):
        self.data = self.user.encrypt_data(value)

    def get_description(self):
        return self.schema._description or ''

    def is_untp(self):
        _vc_types = self.json_data.get("type", [])
        _untp_types= [
            "DigitalConformityCredential",
            "DigitalProductPassport",
            "DigitalFacilityRecord",
            "DigitalTraceabilityEvent"
        ]

        _untp_type = next(filter(lambda x: x in _vc_types, _untp_types), None)
        if _untp_type:
            self.type = _untp_type
        return _untp_type

    def description(self):
        return self.schema.get_schema.get("description")

    def get_type(self, lang=None):
        return self.type

    def get_status(self):
        return self.Status(self.status).label

    def get_datas(self):
        data = self.render()
        credential_subject = ujson.loads(data).get("credentialSubject", {})
        return credential_subject.items()

    @property
    def is_webeth(self):
        return self.issuer_did.type == DID.Types.WEBETH

    def call_oracle(self):

        with open("/shared/" + os.environ["ADMIN_TOKEN_FILE"], "r") as f:
            admin_api_token = f.read().strip()

        oracle_url = f"{settings.API_DLT_URL}/oracle"

        cred = json.loads(self.get_data())

        oracle_payload = {
            'api_token': admin_api_token,
            'Credential': cred
        }
        headers = {'dlt': 'ethereum' }

        response = requests.post(oracle_url, json = oracle_payload, headers = headers).json()

        # mint and allow tokens

        # get operator address and its api_token
        did = self.subject_did
        if did and did.type == DID.Types.WEBETH:
            key_material = json.loads(did.get_key_material())
            operator_api_token = key_material.get('eth_api_token', 'error')
            operator_address = key_material.get('eth_subject_pub_key', 'error')

        mint_url = f"{settings.API_DLT_URL}/mintTokens"
        mint_payload = {
            'api_token': admin_api_token,
            'Address': operator_address
        }
        response = requests.post(mint_url, json = mint_payload, headers = headers).json()

        allow_url = f"{settings.API_DLT_URL}/allowTokens"
        allow_amount = 10000
        allow_payload = {
            'api_token': operator_api_token,
            'Amount': allow_amount
        }

        response = requests.post(allow_url, json = allow_payload, headers = headers).json()

        return response.get('Status') == 'Success'

    def issue(self, did, domain, save=True):
        if self.status == self.Status.ISSUED:
            return

        self.subject_did = did
        self.issued_on = datetime.datetime.now().astimezone(pytz.utc)

        # hash of credential without sign
        self.hash = hashlib.sha3_256(self.render(domain).encode()).hexdigest()

        key = self.issuer_did.get_key_material()
        credential = self.render(domain)

        verify = not settings.DEBUG
        logger.error(verify)
        logger.error("#######################3")

        vc = sign(credential, key, self.issuer_did.did, verify=verify)
        vc_str = json.dumps(vc)

        valid, _ = verify_schema(vc_str, verify=verify)

        if not valid:
            raise Exception(_("The credential is not valid with this schema"))

        valid, _ = verify_signature(vc_str, verify=verify)

        if not valid:
            raise Exception(_("The credential is not valid"))

        self.data = self.user.encrypt_data(vc_str)

        self.status = self.Status.ISSUED

    def get_context(self, domain):
        d = json.loads(self.csv_data)
        issuance_date = ''
        if self.issued_on:
            format = "%Y-%m-%dT%H:%M:%SZ"
            issuance_date = self.issued_on.strftime(format)

        cred_path = 'credentials'
        sid = self.id or 0
        if self.eidas1_did:
            cred_path = 'public/credentials'
            sid = self.hash

        url_id = "{}/{}/{}".format(
            domain,
            cred_path,
            sid
        )

        org = Organization.objects.get(main=True)

        # TODO support revocation
        credential_status_id = 'https://revocation.not.supported/'
        if self.issuer_did.type == DID.Types.WEB:
            credential_status_id = self.issuer_did.did

        context = {
            'id_credential': str(sid),
            'vc_id': url_id,
            'issuer_did': self.issuer_did.did,
            'subject_did': self.subject_did and self.subject_did.did or '',
            'issuance_date': issuance_date,
            'firstName': self.user.first_name or "",
            'lastName': self.user.last_name or "",
            'email': self.user.email,
            'organisation': org.name or '',
            'credential_status_id': credential_status_id,
            'type': self.schema.get_type
        }

        if self.issuer_did.type == DID.Types.WEBETH:
            issuer_key = json.loads(self.issuer_did.get_key_material())
            context['issuer_id'] = issuer_key['eth_issuer_pub_key']

        if self.subject_did and self.subject_did.type == DID.Types.WEBETH:
            subject_key = json.loads(self.subject_did.get_key_material())
            context['subject_did'] = subject_key['eth_subject_pub_key']

        context.update(d)
        return context

    def get_context_untp(self, domain):
        issuance_date = ''
        if self.issued_on:
            format = "%Y-%m-%dT%H:%M:%SZ"
            issuance_date = self.issued_on.strftime(format)

        cred_path = 'credentials'
        sid = self.id or 0
        if self.eidas1_did:
            cred_path = 'public/credentials'
            sid = self.hash

        url_id = "{}/{}/{}".format(
            domain,
            cred_path,
            sid
        )

        org = Organization.objects.get(main=True)

        # TODO support revocation
        credential_status_id = 'https://revocation.not.supported/'
        if self.issuer_did.type == DID.Types.WEB:
            credential_status_id = self.issuer_did.did

        context = {
            'id_credential': str(sid),
            'vc_id': url_id,
            'issuer_did': self.issuer_did.did,
            "issuance_date": issuance_date,
            "name": getattr(org, "name", "") or "",
            "credential_status_id": credential_status_id,
            "schema_id": self.schema.url,
            "subject_id": self.id_string,
            "type": self.type,
        }

        if self.issuer_did.type == DID.Types.WEBETH:
            issuer_key = json.loads(self.issuer_did.get_key_material())
            context['issuer_id'] = issuer_key['eth_issuer_pub_key']

        if self.subject_did and self.subject_did.type == DID.Types.WEBETH:
            subject_key = json.loads(self.subject_did.get_key_material())
            context['subject_did'] = subject_key['eth_subject_pub_key']

        return context

    def render(self, domain=""):
        if (_untp_type := self.is_untp()) is not None:
            return self.render_untp(_untp_type, domain)

        context = self.get_context(domain)
        tmpl = get_template('credentials/base.json')
        d_ordered = ujson.loads(tmpl.render(context))
        if self.schema.context:
            d_ordered["@context"].append(self.schema.context)
        else:
            url_context = urljoin(domain, reverse("idhub:context"))
            d_ordered["@context"].append(url_context)
        d_ordered["credentialSchema"]["id"] = self.schema.url
        d_ordered["name"] = self.schema.get_schema.get("name", [])
        d_ordered["description"] = self.schema.get_schema.get("description", [])
        sch_values = []
        for c in self.schema.get_schema.get("allOf", []):
            sch_subj = c.get("properties", {}).get("credentialSubject", {})
            if sch_subj:
                sch_values = sch_subj.get("properties", {}).keys()

        csv_data = json.loads(self.csv_data)
        for k, v in csv_data.items():
            if k in sch_values:
                d_ordered["credentialSubject"][k] = v

        if "evidence" in csv_data:
            d_ordered["evidence"] = csv_data["evidence"].copy()
        d_minimum = self.filter_dict(d_ordered)

        # You can revoke only didweb
        if not self.is_didweb:
            d_minimum.pop("credentialStatus", None)

        return ujson.dumps(d_minimum)


    def render_untp(self, untp_type, domain=""):
        context = self.get_context_untp(domain)

        tmpl = get_template('credentials/base_untp.json')
        d_ordered = ujson.loads(tmpl.render(context))
        if self.schema.context:
            d_ordered["@context"].append(self.schema.context)
        else:
            url_context = urljoin(domain, reverse("idhub:context"))
            d_ordered["@context"].append(url_context)

        d_ordered["credentialSubject"]= self.json_data.get("credentialSubject", {} )

        d_minimum = self.filter_dict(d_ordered)
        # You can revoke only didweb
        if not self.is_didweb:
            d_minimum.pop("credentialStatus", None)

        return ujson.dumps(d_minimum)

    def get_issued_on(self):
        if self.issued_on:
            return self.issued_on.strftime("%m/%d/%Y")

        return ''

    def set_type(self):
        self.type = self.schema.get_type

    def filter_dict(self, dic):
        new_dict = OrderedDict()
        for key, value in dic.items():
            if isinstance(value, dict):
                new_value = self.filter_dict(value)
                if new_value:
                    new_dict[key] = new_value
            elif value:
                new_dict[key] = value
        return new_dict


class File_datas(models.Model):
    file_name = models.CharField(_("File"), max_length=250)
    success = models.BooleanField(_("Success"), default=True)
    created_at = models.DateTimeField(_("Date"), auto_now=True)


class Membership(models.Model):
    """
      This model represent the relation of this user with the ecosystem.
    """
    class Types(models.IntegerChoices):
        BENEFICIARY = 1, _('Beneficiary')
        EMPLOYEE = 2, _('Employee')
        MEMBER = 3, _('Member')

    type = models.PositiveSmallIntegerField(_('Type of membership'), choices=Types.choices)
    start_date = models.DateField(
        _('Start date'),
        help_text=_('What date did the membership start?'),
        blank=True,
        null=True
    )
    end_date = models.DateField(
        _('End date'),
        help_text=_('What date will the membership end?'),
        blank=True,
        null=True
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='memberships',
    )

    def get_type(self):
        return dict(self.Types.choices).get(self.type)


class Rol(models.Model):
    name = models.CharField(_("name"), max_length=250)
    description = models.CharField(_("Description"), max_length=250, null=True)

    def __str__(self):
        return self.name


class Service(models.Model):
    domain = models.CharField(_("Domain"), max_length=250)
    description = models.CharField(_("Description"), max_length=250)
    rol = models.ManyToManyField(
        Rol,
    )

    def get_roles(self):
        if self.rol.exists():
            return ", ".join([x.name for x in self.rol.order_by("name")])
        return _("None")

    def __str__(self):
        return "{} -> {}".format(self.domain, self.get_roles())


class UserRol(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='roles',
    )
    service = models.ForeignKey(
        Service,
        verbose_name=_("Service"),
        on_delete=models.CASCADE,
        related_name='users',
    )

    class Meta:
        unique_together = ('user', 'service',)
