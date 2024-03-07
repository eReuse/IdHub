import json
import requests
import secrets
import nacl
import base64

from nacl import pwhash, secret
from django.core.cache import cache

from django.conf import settings
from django.http import QueryDict
from django.utils.translation import gettext_lazy as _
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
      and secret_id.
      main is a field which indicates the organization of this idhub 
    """
    name = models.CharField(max_length=250)
    domain = models.CharField(max_length=250, null=True, default=None)
    main = models.BooleanField(default=False)
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
    encrypted_sensitive_data = models.CharField(max_length=255, default=None, null=True)
    salt = models.CharField(max_length=255, default=None, null=True)

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
            redirect_uri=self.response_uri
        )
        auth = (self.my_client_id, self.my_client_secret)
        return requests.get(url, auth=auth)

    def derive_key_from_password(self, password=None):
        if not password:
            password = cache.get("KEY_DIDS").encode('utf-8')

        kdf = pwhash.argon2i.kdf
        ops = pwhash.argon2i.OPSLIMIT_INTERACTIVE
        mem = pwhash.argon2i.MEMLIMIT_INTERACTIVE
        return kdf(
            secret.SecretBox.KEY_SIZE,
            password,
            self.get_salt(),
            opslimit=ops,
            memlimit=mem
        )

    def decrypt_sensitive_data(self, data=None):
        sb_key = self.derive_key_from_password()
        sb = secret.SecretBox(sb_key)
        if not data:
            data = self.get_encrypted_sensitive_data()
        if not isinstance(data, bytes):
            data = data.encode('utf-8')

        return sb.decrypt(data).decode('utf-8')

    def encrypt_sensitive_data(self, data):
        sb_key = self.derive_key_from_password()
        sb = secret.SecretBox(sb_key)
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        
        return base64.b64encode(sb.encrypt(data)).decode('utf-8')

    def get_salt(self):
        if not self.salt:
            return ''
        return base64.b64decode(self.salt.encode('utf-8'))

    def set_salt(self):
        self.salt = base64.b64encode(nacl.utils.random(16)).decode('utf-8')

    def get_encrypted_sensitive_data(self):
        return base64.b64decode(self.encrypted_sensitive_data.encode('utf-8'))

    def set_encrypted_sensitive_data(self):
        key = base64.b64encode(nacl.utils.random(64))
        self.set_salt()

        key_crypted = self.encrypt_sensitive_data(key)
        self.encrypted_sensitive_data = key_crypted

    def encrypt_data(self, data):
        pw = self.decrypt_sensitive_data().encode('utf-8')
        sb = self.get_secret_box(pw)
        value_enc = sb.encrypt(data.encode('utf-8'))
        return base64.b64encode(value_enc).decode('utf-8')

    def decrypt_data(self, data):
        pw = self.decrypt_sensitive_data().encode('utf-8')
        sb = self.get_secret_box(pw)
        value = base64.b64decode(data.encode('utf-8'))
        return sb.decrypt(value).decode('utf-8')

    def get_secret_box(self, password):
        sb_key = self.derive_key_from_password(password=password)
        return secret.SecretBox(sb_key)

    def change_password_key(self, new_password):
        data = self.decrypt_sensitive_data()
        sb_key = self.derive_key_from_password(password=new_password)
        sb = secret.SecretBox(sb_key)
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        
        encrypted_data = base64.b64encode(sb.encrypt(data)).decode('utf-8')
        self.encrypted_sensitive_data = encrypted_data

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

    @property
    def code(self):
        if not self.authorization:
            return ''
        return self.authorization.code

    def verifing(self):
        self.result_verify = verify_presentation(self.vp_token)

    def get_result_verify(self):
        if not self.result_verify:
            return {}
        return json.loads(self.result_verify)

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
        url = self.get_redirect_url()
        if url:
            response["redirect_uri"] = url
        return response

    def get_redirect_url(self):
        if not settings.OIDC_REDIRECT:
            return

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
        return json.dumps(self.user_info, indent=2)
