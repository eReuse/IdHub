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

    def send(self, vp):
        """
          Send the verificable presentation to Verifier
        """
        url = "{url}/verify".format(
            url=self.response_uri.strip("/"),
        )
        auth = (self.my_client_id, self.my_client_secret)
        # import pdb; pdb.set_trace()
        return requests.post(url, data=vp, auth=auth)

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
    # nonce = models.CharField(max_length=50)
    # expected_credentials = models.CharField(max_length=255)
    # expected_contents = models.TextField()
    # action = models.TextField()
    # response_or_redirect = models.CharField(max_length=255)

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
        data = {
            "response_type": "vp_token",
            "response_mode": "direct_post",
            "client_id": self.organization.my_client_id,
            "presentation_definition": self.presentation_definition,
            "nonce": gen_salt(5),
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(data)

        url = '{response_uri}/authorize?{params}'.format(
            response_uri=self.organization.response_uri.strip("/"),
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


class VPVerifyRequest(models.Model):
    """
    `nonce` is an opaque random string used to lookup verification requests. URL-safe.
      Example: "UPBQ3JE2DGJYHP5CPSCRIGTHRTCYXMQPNQ"
    `expected_credentials` is a JSON list of credential types that must be present in this VP.
      Example: ["FinancialSituationCredential", "HomeConnectivitySurveyCredential"]
    `expected_contents` is a JSON object that places optional constraints on the contents of the
      returned VP.
      Example: [{"FinancialSituationCredential": {"financial_vulnerability_score": "7"}}]
    `action` is (for now) a JSON object describing the next steps to take if this verification
      is successful. For example "send mail to <destination> with <subject> and <body>"
      Example: {"action": "send_mail", "params": {"to": "orders@somconnexio.coop", "subject": "New client", "body": ...}
    `response` is a URL that the user's wallet will redirect the user to.
    `submitted_on` is used (by a cronjob) to purge old entries that didn't complete verification
    """
    nonce = models.CharField(max_length=50)
    expected_credentials = models.CharField(max_length=255)
    expected_contents = models.TextField()
    action = models.TextField()
    response_or_redirect = models.CharField(max_length=255)
    submitted_on = models.DateTimeField(auto_now=True)
