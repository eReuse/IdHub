import json
import requests
import secrets

from django.conf import settings
from django.http import QueryDict
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from idhub_auth.models import User
from django.db import models
from utils.idhub_ssikit import verify_presentation


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
      This class represent a member of one net trust or federated host.
      Client_id and client_secret are the credentials of this organization
      get a connection to my. (receive a request)
      My_client_id and my_client_secret are my credentials than to use if I
      want to connect to this organization. (send a request)
      For use the packages requests we need use my_client_id
      For use in the get or post method of a View, then we need use client_id
      and secret_id
    """
    name = models.CharField(max_length=250)
    client_id = models.CharField(
        max_length=24,
        default=set_client_id,
        unique=True
    )
    client_secret = models.CharField(
        max_length=48,
        default=set_client_secret
    )
    my_client_id = models.CharField(
        max_length=24,
    )
    my_client_secret = models.CharField(
        max_length=48,
    )
    response_uri = models.URLField(
        help_text=_("Url where to send the verificable presentation"),
        max_length=250
    )

    def send(self, vp, code):
        """
          Send the verificable presentation to Verifier
        """
        url = "{url}/verify".format(
            url=self.response_uri.strip("/"),
        )
        auth = (self.my_client_id, self.my_client_secret)
        data = {"vp_token": vp}
        if code:
            data["code"] = code

        return requests.post(url, data=data, auth=auth)

    def demand_authorization(self):
        """
          Send the a request for start a process of Verifier
        """
        url = "{url}/verify?demand_uri={redirect_uri}".format(
            url=self.response_uri.strip("/"),
            redirect_uri=settings.RESPONSE_URI
        )
        auth = (self.my_client_id, self.my_client_secret)
        return requests.get(url, auth=auth)

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
    code_used = models.BooleanField(default=False)
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

    def authorize(self, path=None):
        data = {
            "response_type": "vp_token",
            "response_mode": "direct_post",
            "client_id": self.organization.my_client_id,
            "presentation_definition": self.presentation_definition,
            "code": self.code,
            "nonce": gen_salt(5),
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(data)

        response_uri = self.organization.response_uri.strip("/")
        if path:
            response_uri = "{}/{}".format(response_uri, path.strip("/"))

        url = '{response_uri}/authorize?{params}'.format(
            response_uri=response_uri,
            params=query_dict.urlencode()
        )
        return url


class OAuth2VPToken(models.Model):
    """
      This class represent the response of Wallet to Verifier
      and the result of verify.
    """
    created = models.DateTimeField(auto_now=True)
    result_verify = models.CharField(max_length=255)
    vp_token = models.TextField()
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
        related_name='vp_tokens',
        null=True,
    )

    def __init__(self, *args, **kwargs):
        code = kwargs.pop("code", None)
        super().__init__(*args, **kwargs)
        
        self.authorization = Authorization.objects.filter(code=code).first()

    def verifing(self):
        self.result_verify = verify_presentation(self.vp_token)

    def get_response_verify(self):
        response = {
            "verify": ',',
            "redirect_uri": "",
            "response": "",
        }
        verification = json.loads(self.result_verify)
        if verification.get('errors') or verification.get('warnings'):
            response["verify"] = "Error, Verification Failed"
            return response
        
        response["verify"] = "Ok, Verification correct"
        response["redirect_uri"] = self.get_redirect_url()
        return response

    def get_redirect_url(self):
        data = {
            "code": self.authorization.code,
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(data)

        response_uri = settings.ALLOW_CODE_URI

        url = '{response_uri}?{params}'.format(
            response_uri=response_uri,
            params=query_dict.urlencode()
        )
        return url

    def get_user_info(self):
        tk = json.loads(self.vp_token)
        self.user_info = tk.get(
            "verifiableCredential", [{}]
        )[-1].get("credentialSubject")
