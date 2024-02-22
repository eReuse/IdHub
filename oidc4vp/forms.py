import json

from django import forms
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from utils.idhub_ssikit import create_verifiable_presentation
from idhub.models import VerificableCredential


class AuthorizeForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.data = kwargs.get('data', {}).copy()
        self.user = kwargs.pop('user', None)
        self.org = kwargs.pop('org', None)
        self.code = kwargs.pop('code', None)
        self.presentation_definition = kwargs.pop('presentation_definition', [])
        self.subject_did = None

        reg = r'({})'.format('|'.join(self.presentation_definition))

        self.all_credentials = self.user.vcredentials.filter(
           type__iregex=reg,
        )
        self.credentials = self.all_credentials.filter(
            status=VerificableCredential.Status.ISSUED.value
        )
        super().__init__(*args, **kwargs)
        for vp in self.presentation_definition:
            vp = vp.lower()
            choices = [
                (str(x.id), x.type.lower()) for x in self.credentials.filter(
                    type__iexact=vp)
            ]
            self.fields[vp.lower()] = forms.ChoiceField(
                widget=forms.RadioSelect,
                choices=choices
            )
    def clean(self):
        data = super().clean()
        self.list_credentials = []
        for c in self.credentials:
            if str(c.id) == data.get(c.type.lower()):
                if c.status is not c.Status.ISSUED.value or not c.data:
                    txt = _('There are some problems with this credentials')
                    raise ValidationError(txt)

                cred = self.user.decrypt_data(
                    c.data,
                )
                self.subject_did = c.subject_did
                self.list_credentials.append(cred)

        if not self.code:
            txt = _("There isn't code in request")
            raise ValidationError(txt)

        return data

    def save(self, commit=True):
        if not self.list_credentials:
            return

        self.get_verificable_presentation()

        if commit:
            return self.org.send(self.vp, self.code)

        return

    def get_verificable_presentation(self):
        did = self.subject_did
        vp_template = get_template('credentials/verifiable_presentation.json')
        vc_list = json.dumps([json.loads(x) for x in self.list_credentials])

        context = {
            "holder_did": did.did,
            "verifiable_credential_list": vc_list
        }
        unsigned_vp = vp_template.render(context)
        key_material = did.get_key_material()
        self.vp = create_verifiable_presentation(key_material, unsigned_vp)
