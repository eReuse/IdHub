from django.db import models
from django.contrib.auth.models import User as DjangoUser


class AppUser(models.Model):
    # Ya incluye "first_name", "last_name", "email", y "date_joined" heredando de la clase User de django.
    # Falta ver que más información hay que añadir a nuestros usuarios, como los roles etc.
    django_user = models.OneToOneField(DjangoUser, on_delete=models.CASCADE)

    # Extra data, segun entidad/organizacion
    pass


class Event(models.Model):
    # Para los "audit logs" que se requieren en las pantallas.
    timestamp = models.DateTimeField()
    kind = "PLACEHOLDER"












class ExternallyStoredModel(models.Model):
    pass

    # Any models which inherit from this class are stored in wallet-kit, not in the Django ORM
    class Meta:
        abstract = True

    @staticmethod
    def from_json(json_serialization):
        # Construct an instance of this class by de-serialization from data returned by wallet-kit.
        # Must be implemented by any deriving class.
        raise NotImplementedError()


class DID(ExternallyStoredModel):
    did_string = models.CharField(max_length=250)
    # kind = "KEY|JWK|WEB|EBSI|CHEQD|IOTA"


class VerifiableCredential(ExternallyStoredModel):
    id_string = models.CharField(max_length=250)
    data = models.TextField()
    verified = models.BooleanField()
    created_on = models.DateTimeField()
    did_issuer = models.CharField(max_length=250)  # Probably not a FK but the DID directly
    did_subject = models.CharField(max_length=250)  # Probably not a FK but the DID directly
