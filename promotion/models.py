from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from oidc4vp.models import Authorization


class Promotion(models.Model):
    class Types(models.IntegerChoices):
        VULNERABLE = 1, _("Financial vulnerability")

    name = models.CharField(max_length=250)
    discount = models.PositiveSmallIntegerField(
        choices=Types.choices,
    )
    authorize = models.ForeignKey(
        Authorization,
        on_delete=models.CASCADE,
        related_name='promotions',
        null=True,
    )

    def get_url(self, code):
        url = "{}?code={}".format(
            reverse_lazy("promotion:contract"),
            code
        )

    def get_discount(self, price):
        return price - price*0.25

