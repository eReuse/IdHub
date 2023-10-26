import json
from django.db import models
from django.utils.translation import gettext_lazy as _
from idhub_auth.models import User


# class Event(models.Model):
    # Para los "audit logs" que se requieren en las pantallas.
    # timestamp = models.DateTimeField()
    # Los eventos no tienen relación con otros objetos a nivel de BBDD.
    # event_data = models.CharField(max_length=250)


class DID(models.Model):
    created_at = models.DateTimeField(auto_now=True)
    did = models.CharField(max_length=250, unique=True)
    label = models.CharField(max_length=50)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dids',
        null=True,
    )
    # kind = "KEY|WEB"


class Schemas(models.Model):
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


class VerifiableCredential(models.Model):
    """
        Definition of Verificable Credentials
    """
    class Status(models.IntegerChoices):
        ENABLE = 1, _("Enable")
        ISSUED = 2, _("Issued")
        REVOKED = 3, _("Revoked")
        EXPIRED = 4, _("Expired")

    id_string = models.CharField(max_length=250)
    verified = models.BooleanField()
    created_on = models.DateTimeField(auto_now=True)
    issuer_on = models.DateTimeField(null=True)
    did_issuer = models.CharField(max_length=250)
    did_subject = models.CharField(max_length=250)
    data = models.TextField()
    status = models.PositiveSmallIntegerField(
        choices=Status.choices,
        default=Status.ENABLE
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vcredentials',
    )

    @property
    def get_schema(self):
        if not self.data:
            return {}
        return json.loads(self.data)

    def type(self):
        return self.get_schema.get('name', '')

    def description(self):
        return self.get_schema.get('description', '')

    def get_status(self):
        return self.Status(self.status).label

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
        PARTNER = 3, _('Partner')

    type = models.PositiveSmallIntegerField(_('Type of membership'), choices=Types.choices)
    start_date = models.DateField(
        _('Start date'),
        help_text=_('What date did the membership start?'),
        blank=True,
        null=True
    )
    end_date = models.DateField(
        _('End date'),
        help_text=_('What date did the membership end?'),
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
    name = models.CharField(max_length=250)

    def __str__(self):
        return self.name


class Service(models.Model):
    domain = models.CharField(max_length=250)
    description = models.CharField(max_length=250)
    rol = models.ManyToManyField(
        Rol,
    )

    def get_roles(self):
        return ", ".join([x.name for x in self.rol.all()])
    
    def __str__(self):
        return "{} -> {}".format(self.domain, self.rol.name)


class UserRol(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='roles',
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='users',
    )
