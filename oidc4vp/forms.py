import json
import requests

from django import forms
from django.conf import settings
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from utils.idhub_ssikit import create_verifiable_presentation
from oidc4vp.models import Organization


class AuthorizeForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.data = kwargs.get('data', {}).copy()
        self.user = kwargs.pop('user', None)
        self.org = kwargs.pop('org', None)
        self.presentation_definition = kwargs.pop('presentation_definition', [])

        reg = r'({})'.format('|'.join(self.presentation_definition))

        self.credentials = self.user.vcredentials.filter(
            schema__type__iregex=reg
        )
        super().__init__(*args, **kwargs)
        for vp in self.presentation_definition:
            vp = vp.lower()
            choices = [
                (str(x.id), x.schema.type.lower()) for x in self.credentials.filter(
                    schema__type__iexact=vp)
            ]
            self.fields[vp.lower()] = forms.ChoiceField(
                widget=forms.RadioSelect,
                choices=choices
            )
    def clean(self):
        data = super().clean()
        self.list_credentials = []
        for c in self.credentials:
            if str(c.id) == data.get(c.schema.type.lower()):
                if c.status is not c.Status.ISSUED.value or not c.data:
                    txt = _('There are some problems with this credentials')
                    raise ValidationError(txt)

                self.list_credentials.append(c)

        return data

    def save(self, commit=True):
        if not self.list_credentials:
            return

        self.get_verificable_presentation()

        if commit:
            return self.org.send(self.vp)

        return

    def get_verificable_presentation(self):
        did = self.list_credentials[0].subject_did
        vp_template = get_template('credentials/verifiable_presentation.json')
        vc_list = json.dumps([json.loads(x.data) for x in self.list_credentials])

        context = {
            "holder_did": did.did,
            "verifiable_credential_list": vc_list
        }
        unsigned_vp = vp_template.render(context)
        self.vp = create_verifiable_presentation(did.key_material, unsigned_vp)
