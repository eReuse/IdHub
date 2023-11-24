import requests

from django.db import models
from django.http import QueryDict
from django.utils.translation import gettext_lazy as _
from idhub_auth.models import User


class Organization(models.Model):
    name = models.CharField(max_length=250)
    client_id = models.CharField()
    client_secret = models.CharField()
    response_uri = models.URLField(
        help_text=_("Url where to send the presentation"),
        max_length=250
    )

    def __str__(self):
        return self.name

    def send(self, vcred):
        return requests.post(self.url, data=vcred)


class Authorization(models.Model):
    created = models.DateTimeField(auto_now=True)
    presentation_definition = models.CharField()
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='vp_tokens',
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
            "client_id": "...",
            "response_uri": response_uri,
            "presentation_definition": "...",
            "nonce": ""
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(data)

        url = '{response_uri}/authorize?{params}'.format(
            response_uri=self.organization.response_uri,
            params=query_dict.urlencode()
        )

class OAuth2VPToken(models.Model):
    created = models.DateTimeField(auto_now=True)
    response_code = models.CharField()
    result_verify = models.BooleanField()
    presentation_definition = models.CharField()
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

