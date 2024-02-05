from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from idhub.models import DID, VerificableCredential
from oidc4vp.models import Organization
from idhub_auth.models import User


class ProfileForm(forms.ModelForm):
    MANDATORY_FIELDS = ['first_name', 'last_name', 'email']

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


class TermsConditionsForm(forms.Form):
    accept_privacy = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    accept_legal = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    accept_cookies = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def get_label(self, url, read):
        label = _('I read and accepted the')
        label += f' <a class="btn btn-green-user" target="_blank" href="{url}" '
        label += f'title="{read}">{read}</a>'
        return label

    def privacy_label(self):
        url = "https://laweb.pangea.org/politica-de-privacitat/"
        read = _("Read privacy policy")
        return self.get_label(url, read)

    def legal_label(self):
        url = "https://laweb.pangea.org/avis-legal/"
        read = _("Read legal policy")
        return self.get_label(url, read)

    def cookies_label(self):
        url = "https://laweb.pangea.org/politica-de-cookies-2/"
        read = _("Read cookies policy")
        return self.get_label(url, read)

    def clean(self):
        data = self.cleaned_data
        privacy = data.get("accept_privacy")
        legal = data.get("accept_legal")
        cookies = data.get("accept_cookies")
        if privacy and legal and cookies:
            self.user.accept_gdpr = True
        else:
            self.user.accept_gdpr = False        
        return data
        
    def save(self, commit=True):

        if commit:
            self.user.save()
            return self.user
        
        return 


class RequestCredentialForm(forms.Form):
    did = forms.ChoiceField(label=_("Did"), choices=[])
    credential = forms.ChoiceField(label=_("Credential"), choices=[])

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.lang = kwargs.pop('lang', None)
        self._domain = kwargs.pop('domain', None)
        self.password = kwargs.pop('password', None)
        super().__init__(*args, **kwargs)
        self.fields['did'].choices = [
            (x.did, x.label) for x in DID.objects.filter(user=self.user)
        ]
        self.fields['credential'].choices = [
            (x.id, x.get_type(lang=self.lang)) for x in VerificableCredential.objects.filter(
                user=self.user,
                status=VerificableCredential.Status.ENABLED
            )
        ]

    def save(self, commit=True):
        did = DID.objects.filter(
            user=self.user,
            did=self.data['did']
        )
        cred = VerificableCredential.objects.filter(
            user=self.user,
            id=self.data['credential'],
            status=VerificableCredential.Status.ENABLED
        )
        if not all([cred.exists(), did.exists()]):
            return

        did = did[0]
        cred = cred[0]
        try:
            if self.password:
                cred.issue(did, self.password, domain=self._domain)
        except Exception:
            return

        if commit:
            cred.save()
            return cred
        
        return 


class DemandAuthorizationForm(forms.Form):
    organization = forms.ChoiceField(label=_("Organization"), choices=[])

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['organization'].choices = [
            (x.id, x.name) for x in Organization.objects.filter() 
                if x.response_uri != settings.RESPONSE_URI
        ]

    def save(self, commit=True):
        self.org = Organization.objects.filter(
            id=self.data['organization']
        )
        if not self.org.exists():
            return

        self.org = self.org[0]

        if commit:
            url = self.org.demand_authorization()
            if url.status_code == 200:
                return url.json().get('redirect_uri')
        
        return 

