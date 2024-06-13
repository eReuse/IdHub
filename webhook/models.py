from django.db import models

# Create your models here.


class Token(models.Model):
    token = models.UUIDField()
