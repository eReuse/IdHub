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

    
class MemberFederated(models.Model):
    dlt_id_provider = models.IntegerField(primary_key=True)
    domain = models.CharField(max_length=STR_EXTEND_SIZE)
    # This client_id and client_secret is used for connected to this domain as
    # a client and this domain then is the server of auth
    client_id = models.CharField(max_length=STR_EXTEND_SIZE, null=True)
    client_secret = models.CharField(max_length=STR_EXTEND_SIZE, null=True)
    institution = models.ForeignKey(
        Institution, on_delete=models.SET_NULL, null=True, blank=True)


class UserDpp(models.Model):
    roles_dlt = models.TextField()
    api_keys_dlt = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
