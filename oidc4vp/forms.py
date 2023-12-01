from django import forms
from django.conf import settings

from utils.idhub_ssikit import issue_verifiable_presentation
from oidc4vp.models import Organization


class AuthorizeForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.data = kwargs.get('data', {}).copy()
        self.user = kwargs.pop('user', None)
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
        import pdb; pdb.set_trace()
        self.list_credentials = []
        for c in self.credentials:
            if str(c.id) == data.get(c.schema.type.lower()):
                self.list_credentials.append(c)
        return data

    def save(self, commit=True):
        if not self.list_credentials:
            return

        did = self.list_credentials[0].subject_did

        self.vp = issue_verifiable_presentation(
            vp_template: Template,
            vc_list: list[str],
            jwk_holder: str,
            holder_did: str)

        self.vp = issue_verifiable_presentation(
            vp_template: Template,
            self.list_credentials,
            did.key_material,
            did.did)

        if commit:
            result = requests.post(self.vp)
            return result

        return

