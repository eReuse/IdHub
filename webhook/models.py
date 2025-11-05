from django.db import models
from django.utils.translation import gettext_lazy as _
from idhub_auth.models import User

# Create your models here.


class Token(models.Model):
    token = models.UUIDField()
    label = models.CharField(_("Label"), max_length=250, default="")
    active = models.BooleanField(_("Active"), default=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
