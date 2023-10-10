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
    # Los eventos no tienen relación con otros objetos a nivel de BBDD.
    event_data = models.CharField(max_length=250)


class DID(models.Model):
    did_string = models.CharField(max_length=250)
    label = models.CharField(max_length=50)
    owner = models.ForeignKey(AppUser, on_delete=models.CASCADE)
    # kind = "KEY|WEB"


class VerifiableCredential(models.Model):
    id_string = models.CharField(max_length=250)
    verified = models.BooleanField()
    created_on = models.DateTimeField()
    did_issuer = models.CharField(max_length=250)
    did_subject = models.CharField(max_length=250)
    owner = models.ForeignKey(AppUser, on_delete=models.CASCADE)
    data = models.TextField()


class VCTemplate(models.Model):
    wkit_template_id = models.CharField(max_length=250)
    data = models.TextField()


