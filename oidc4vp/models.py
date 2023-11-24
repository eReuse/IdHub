import requests
import secrets

from django.conf import settings
from django.http import QueryDict
from django.utils.translation import gettext_lazy as _
from idhub_auth.models import User
from django.db import models


SALT_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def gen_salt(length: int) -> str:
    """Generate a random string of SALT_CHARS with specified ``length``."""
    if length <= 0:
        raise ValueError("Salt length must be positive")
    
    return "".join(secrets.choice(SALT_CHARS) for _ in range(length))


def set_client_id():
    return gen_salt(24)


def set_client_secret():
    return gen_salt(48)


def set_code():
    return gen_salt(24)


class Organization(models.Model):
    """
      This class represent a member of one net trust or federated host
    """
    name = models.CharField(max_length=250)
    client_id = models.CharField(max_length=24, default=set_client_id)
    client_secret = models.CharField(max_length=48, default=set_client_secret)
    response_uri = models.URLField(
        help_text=_("Url where to send the verificable presentation"),
        max_length=250
    )

    def send(self, vp):
        """
          Send the verificable presentation to Verifier
        """
        org = Organization.objects.get(
            response_uri=settings.RESPONSE_URI
        )
        auth = (org.client_id, org.client_secret)
        return requests.post(self.url, data=vp, auth=auth)

    def __str__(self):
        return self.name


###################
# Verifier clases #
###################


class Authorization(models.Model):
    """
      This class represent a query through browser the client to the wallet.
      The Verifier need to do a redirection to the user to Wallet.
      The code we use as a soft foreing key between Authorization and OAuth2VPToken.
    """
    code = models.CharField(max_length=24, default=set_code)
    created = models.DateTimeField(auto_now=True)
    presentation_definition = models.CharField(max_length=250)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='authorizations',
        null=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
    )

    def authorize(self):
        response_uri = self.__class__.objects.filter(
            response_uri=settings.RESPONSE_URI
        )
        data = {
            "response_type": "vp_token",
            "response_mode": "direct_post",
            "client_id": self.organization.client_id,
            "response_uri": response_uri,
            "presentation_definition": "...",
            "nonce": gen_salt(5),
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(data)

        url = '{response_uri}/authorize?{params}'.format(
            response_uri=self.organization.response_uri,
            params=query_dict.urlencode()
        )
        return url


class OAuth2VPToken(models.Model):
    """
      This class represent the response of Wallet to Verifier
      and the result of verify.
    """
    created = models.DateTimeField(auto_now=True)
    code = models.CharField(max_length=250)
    result_verify = models.BooleanField(max_length=250)
    presentation_definition = models.CharField(max_length=250)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='vp_tokens',
        null=True,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vp_tokens',
        null=True,
    )
    authorization = models.ForeignKey(
        Authorization,
        on_delete=models.SET_NULL,
        null=True,
    )

    def verifing(self):
        pass

