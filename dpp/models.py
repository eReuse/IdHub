from django.db import models
from user.models import User, Institution
from utils.constants import STR_EXTEND_SIZE
# Create your models here.


class Proof(models.Model):
    ## The signature can be a phid or dpp depending of type of Proof
    timestamp = models.IntegerField()
    uuid = models.UUIDField()
    signature = models.CharField(max_length=STR_EXTEND_SIZE)
    type = models.CharField(max_length=STR_EXTEND_SIZE)
    issuer = models.ForeignKey(Institution, on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
