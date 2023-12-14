import json
import pytz
import datetime
from django.db import models
from django.conf import settings
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from utils.idhub_ssikit import (
    generate_did_controller_key,
    keydid_from_controller_key,
    sign_credential,
)
from idhub_auth.models import User


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
        EV_CREDENTIAL_DELETED = 12, "Credential deleted"
        EV_CREDENTIAL_ISSUED_FOR_USER = 13, "Credential issued for user"
        EV_CREDENTIAL_ISSUED = 14, "Credential issued"
        EV_CREDENTIAL_PRESENTED_BY_USER = 15, "Credential presented by user"
        EV_CREDENTIAL_PRESENTED = 16, "Credential presented"
        EV_CREDENTIAL_ENABLED = 17, "Credential enabled"
        EV_CREDENTIAL_CAN_BE_REQUESTED = 18, "Credential available"
        EV_CREDENTIAL_REVOKED_BY_ADMIN = 19, "Credential revoked by admin"
        EV_CREDENTIAL_REVOKED = 20, "Credential revoked"
        EV_ROLE_CREATED_BY_ADMIN = 21, "Role created by admin"
        EV_ROLE_MODIFIED_BY_ADMIN = 22, "Role modified by admin"
        EV_ROLE_DELETED_BY_ADMIN = 23, "Role deleted by admin"
        EV_SERVICE_CREATED_BY_ADMIN = 24, "Service created by admin"
        EV_SERVICE_MODIFIED_BY_ADMIN = 25, "Service modified by admin"
        EV_SERVICE_DELETED_BY_ADMIN = 26, "Service deleted by admin"
        EV_ORG_DID_CREATED_BY_ADMIN = 27, "Organisational DID created by admin"
        EV_ORG_DID_DELETED_BY_ADMIN = 28, "Organisational DID deleted by admin"
        EV_USR_DEACTIVATED_BY_ADMIN = 29, "User deactivated"
        EV_USR_ACTIVATED_BY_ADMIN = 30, "User activated"

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
        msg += "['field1':'value1', 'field2':'value2'>,...]".format(
            username=user.username,
        )
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
            type=cred.type(),
            id=cred.id,
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_DELETED_BY_ADMIN,
            message=msg,
        )
        
    @classmethod
    def set_EV_CREDENTIAL_DELETED(cls, cred):
        msg = _("The credential of type '{type}' and ID: '{id}' was deleted from your wallet").format(
            type=cred.type(),
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
            type=cred.type(),
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
            type=cred.type(),
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
            type=cred.type(),
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
            type=cred.type(),
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
            type=cred.type(),
            username=cred.user.username
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_ENABLED,
            message=msg,
        )
        
    @classmethod
    def set_EV_CREDENTIAL_CAN_BE_REQUESTED(cls, cred):
        msg = _("You can request the '{type}' credential").format(
            type=cred.type()
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_CAN_BE_REQUESTED,
            message=msg,
            user=cred.user
        )
        
    @classmethod
    def set_EV_CREDENTIAL_REVOKED_BY_ADMIN(cls, cred):
        msg = _("The credential of type '{type}' and ID: '{id}' was revoked for ").format(
            type=cred.type(),
            id=cred.id
        )
        cls.objects.create(
            type=cls.Types.EV_CREDENTIAL_REVOKED_BY_ADMIN,
            message=msg,
        )
        
    @classmethod
    def set_EV_CREDENTIAL_REVOKED(cls, cred):
        msg = _("The credential of type '{type}' and ID: '{id}' was revoked by admin").format(
            type=cred.type(),
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
        

class DID(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    label = models.CharField(_("Label"), max_length=50)
    did = models.CharField(max_length=250)
    # In JWK format. Must be stored as-is and passed whole to library functions.
    # Example key material:
    # '{"kty":"OKP","crv":"Ed25519","x":"oB2cPGFx5FX4dtS1Rtep8ac6B__61HAP_RtSzJdPxqs","d":"OJw80T1CtcqV0hUcZdcI-vYNBN1dlubrLaJa0_se_gU"}'
    key_material = models.CharField(max_length=250)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dids',
        null=True,
    )

    @property
    def is_organization_did(self):
        if not self.user:
            return True
        return False

    def set_did(self):
        self.key_material = generate_did_controller_key()
        self.did = keydid_from_controller_key(self.key_material)

    def get_key(self):
        return json.loads(self.key_material)


class Schemas(models.Model):
    type = models.CharField(max_length=250)
    file_schema = models.CharField(max_length=250)
    data = models.TextField()
    created_at = models.DateTimeField(auto_now=True)

    @property
    def get_schema(self):
        if not self.data:
            return {}
        return json.loads(self.data)

    def name(self):
        return self.get_schema.get('name', '')

    def description(self):
        return self.get_schema.get('description', '')


class VerificableCredential(models.Model):
    """
        Definition of Verificable Credentials
    """
    class Status(models.IntegerChoices):
        ENABLED = 1, _("Enabled")
        ISSUED = 2, _("Issued")
        REVOKED = 3, _("Revoked")
        EXPIRED = 4, _("Expired")

    id_string = models.CharField(max_length=250)
    verified = models.BooleanField()
    created_on = models.DateTimeField(auto_now=True)
    issued_on = models.DateTimeField(null=True)
    data = models.TextField()
    csv_data = models.TextField()
    status = models.PositiveSmallIntegerField(
        choices=Status.choices,
        default=Status.ENABLED
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vcredentials',
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
    schema = models.ForeignKey(
        Schemas,
        on_delete=models.CASCADE,
        related_name='vcredentials',
    )

    def type(self):
        return self.schema.type

    def description(self):
        for des in json.loads(self.render()).get('description', []):
            if settings.LANGUAGE_CODE == des.get('lang'):
                return des.get('value', '')
        return ''

    def get_status(self):
        return self.Status(self.status).label

    def get_datas(self):
        data = json.loads(self.csv_data).items()
        return data

    def issue(self, did):
        if self.status == self.Status.ISSUED:
            return

        self.status = self.Status.ISSUED
        self.subject_did = did
        self.issued_on = datetime.datetime.now().astimezone(pytz.utc)
        self.data = sign_credential(
            self.render(),
            self.issuer_did.key_material
        )

    def get_context(self):
        d = json.loads(self.csv_data)
        issuance_date = ''
        if self.issued_on:
            format = "%Y-%m-%dT%H:%M:%SZ"
            issuance_date = self.issued_on.strftime(format)

        context = {
            'vc_id': self.id,
            'issuer_did': self.issuer_did.did,
            'subject_did': self.subject_did and self.subject_did.did or '',
            'issuance_date': issuance_date,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        }
        context.update(d)
        return context

    def render(self):
        context = self.get_context()
        template_name = 'credentials/{}'.format(
            self.schema.file_schema
        )
        tmpl = get_template(template_name)
        return tmpl.render(context)


    def get_issued_on(self):
        if self.issued_on:
            return self.issued_on.strftime("%m/%d/%Y")

        return ''

class VCTemplate(models.Model):
    wkit_template_id = models.CharField(max_length=250)
    data = models.TextField()


class File_datas(models.Model):
    file_name = models.CharField(max_length=250)
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now=True)


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
            return ", ".join([x.name for x in self.rol.all()])
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
