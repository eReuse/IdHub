
import json
import requests

from django import forms
from django.conf import settings
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from utils.idhub_ssikit import create_verifiable_presentation
from oidc4vp.models import Organization, Authorization
from promotion.models import Promotion


class WalletForm(forms.Form):
    organization = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        self.presentation_definition = kwargs.pop('presentation_definition', [])
        super().__init__(*args, **kwargs)
        self.fields['organization'].choices = [
            (x.id, x.name) for x in Organization.objects.exclude(
                domain=settings.DOMAIN
            ) 
        ]

    def save(self, commit=True):
        self.org = Organization.objects.filter(
            id=self.data['organization']
        )
        if not self.org.exists():
            return

        self.org = self.org[0]

        self.authorization = Authorization(
            organization=self.org,
            presentation_definition=self.presentation_definition,
        )
        self.promotion = Promotion(
            discount = Promotion.Types.VULNERABLE.value,
            authorize = self.authorization
        )

        if commit:
            self.authorization.save()
            self.promotion.save()

            return self.authorization.authorize()
        
        return 

    
class ContractForm(forms.Form):
    nif = forms.CharField()
    name = forms.CharField()
    first_last_name = forms.CharField()
    second_last_name = forms.CharField()
    email = forms.CharField()
    email_repeat = forms.CharField()
    telephone = forms.CharField()
    birthday = forms.CharField()
    gen = forms.CharField()
    lang = forms.CharField()

