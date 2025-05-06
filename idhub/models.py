import json
import ujson
import pytz
import hashlib
import logging
import datetime
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
from pyvckit.verify import verify_vc

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
        EV_CREDENTIAL_CAN_BE_REQUESTED = 19, "Credential available"
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
            message=msg,
        )


class DID(models.Model):
    class Types(models.IntegerChoices):
        WEB = 1, "Web"
        KEY = 2, "Key"
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
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dids',
        null=True,
    )
    # JSON-serialized DID document
    didweb_document = models.TextField()

    @property
    def is_organization_did(self):
        if not self.user:
            return True
        return False

    def get_key_material(self):
        user = self.user or self.get_organization()
        return user.decrypt_data(self.key_material)

    def set_key_material(self, value):
        user = self.user or self.get_organization()
        if not user.encrypted_sensitive_data:
            user.set_encrypted_sensitive_data()
            user.save()
        self.key_material = user.encrypt_data(value)

    def set_did(self):
        new_key_material = generate_keys()
        self.set_key_material(new_key_material)

        if self.type == self.Types.KEY:
            self.did = generate_did(new_key_material)
        elif self.type == self.Types.WEB:
            url = "https://{}".format(settings.DOMAIN)
            path = reverse("idhub:serve_did", args=["a"])

            if path:
                path = path.split("/a/did.json")[0]
                url = "https://{}/{}".format(settings.DOMAIN, path)

            self.did = generate_did(new_key_material, url)
            key = json.loads(new_key_material)
            url, self.didweb_document = gen_did_document(self.did, key)

    def get_key(self):
        return json.loads(self.key_material)

    def get_organization(self):
        return Organization.objects.get(main=True)

    def get_path(self):
        did_id = self.did.split(':')[-1]
        return reverse("idhub:serve_did", args=[did_id])

    def has_link(self):
        linked_types = [self.Types.WEB]
        if self.type in linked_types:
            return True
        return False

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
    name = models.CharField(_("Name"), max_length=250)
    data = models.FileField(upload_to='uploads/')


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
    hash = models.CharField(max_length=260)
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

    def issue(self, did, domain, save=True):
        if self.status == self.Status.ISSUED:
            return

        # TODO cleanup commented:

        # supported = False
        # for name in self.schema.get_schema.get("name"):
        #     if name.get("value") in settings.SUPPORTED_CREDENTIALS:
        #         supported = True

        # if not supported:
        #     return

        self.subject_did = did
        self.issued_on = datetime.datetime.now().astimezone(pytz.utc)

        # hash of credential without sign
        self.hash = hashlib.sha3_256(self.render(domain).encode()).hexdigest()

        key = self.issuer_did.get_key_material()
        credential = self.render(domain)

        vc = sign(credential, key, self.issuer_did.did)
        vc_str = json.dumps(vc)
        valid = verify_vc(vc_str)

        if not valid:
            raise Exception(_("The credential is not valid"))

        if not save:
            return vc_str

        self.data = self.user.encrypt_data(vc_str)

        self.status = self.Status.ISSUED

    def get_context(self, domain):
        d = json.loads(self.csv_data)
        issuance_date = ''
        if self.issued_on:
            format = "%Y-%m-%dT%H:%M:%SZ"
            issuance_date = self.issued_on.strftime(format)

        cred_path = 'credentials'
        sid = self.id
        if self.eidas1_did:
            cred_path = 'public/credentials'
            sid = self.hash

        url_id = "{}/{}/{}".format(
            domain,
            cred_path,
            sid
        )

        org = Organization.objects.get(main=True)

        credential_status_id = 'https://revocation.not.supported/'
        if self.issuer_did.type == DID.Types.WEB:
            credential_status_id = self.issuer_did.did

        context = {
            'id_credential': str(self.id),
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
        context.update(d)
        return context


    def render(self, domain=""):
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

        for k, v in json.loads(self.csv_data).items():
            if k in sch_values:
                d_ordered["credentialSubject"][k] = v

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
