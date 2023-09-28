from django.db import models
from django.contrib.auth.models import User as DjangoUser


class User(DjangoUser):
    # Ya incluye "first_name", "last_name", "email", y "date_joined" heredando de la clase User de django.
    # Falta ver que más información hay que añadir a nuestros usuarios, como los roles etc.
    pass


class Event(models.Model):
    # Para los "audit logs" que se requieren en las pantallas.
    timestamp = models.DateTimeField()
    kind = "PLACEHOLDER"


class DID(models.Model):
    did_string = models.CharField(max_length=250)
    # kind = "KEY|JWK|WEB|EBSI|CHEQD|IOTA"


class VerifiableCredential(models.Model):
    id_string = models.CharField(max_length=250)
    data = models.TextField()
    verified = models.BooleanField()
    created_on = models.DateTimeField()
    did_issuer = models.ForeignKey(DID, on_delete=models.PROTECT)
    did_subject = models.ForeignKey(DID, on_delete=models.PROTECT)
