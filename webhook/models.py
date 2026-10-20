import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from idhub.models import DID
from idhub_auth.models import User

# Create your models here.


class Token(models.Model):
    token = models.UUIDField(default=uuid.uuid4, blank=True, null=True)
    label = models.CharField(_("Label"), max_length=250, default="")
    active = models.BooleanField(_("Active"), default=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    allowed_dids = models.ManyToManyField(
        DID,
        blank=True,
        related_name='tokens',
        verbose_name=_("Allowed DIDs"),
        help_text=_("Select the DIDs this token is permitted to use.")
    )
