import requests
from django import forms
from django.conf import settings
from idhub_auth.models import User
from idhub.models import DID, VerificableCredential
from oidc4vp.models import Organization


class ProfileForm(forms.ModelForm):
    MANDATORY_FIELDS = ['first_name', 'last_name', 'email']

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


class RequestCredentialForm(forms.Form):
    did = forms.ChoiceField(choices=[])
    credential = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['did'].choices = [
            (x.did, x.label) for x in DID.objects.filter(user=self.user)
        ]
        self.fields['credential'].choices = [
            (x.id, x.type()) for x in VerificableCredential.objects.filter(
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

        did = did[0].did
        cred = cred[0]
        try:
            cred.issue(did)
        except Exception:
            return

        if commit:
            cred.save()
            return cred
        
        return 


class DemandAuthorizationForm(forms.Form):
    organization = forms.ChoiceField(choices=[])

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
            auth = (self.org.client_id, self.org.client_secret)
            if url.status_code == 200:
                return url.json().get('redirect_uri')
        
        return 

    
class CredentialPresentationForm(forms.Form):
    organization = forms.ChoiceField(choices=[])
    # credential = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['organization'].choices = [
            (x.id, x.name) for x in Organization.objects.filter()
        ]
        # self.fields['credential'].choices = [
        #     (x.id, x.type()) for x in VerificableCredential.objects.filter(
        #         user=self.user,
        #         status=VerificableCredential.Status.ISSUED
        #     )
        # ]

    def save(self, commit=True):
        self.org = Organization.objects.filter(
            id=self.data['organization']
        )
        self.cred = VerificableCredential.objects.filter(
            user=self.user,
            id=self.data['credential'],
            status=VerificableCredential.Status.ISSUED
        )
        if not all([self.org.exists(), self.cred.exists()]):
            return

        self.org = self.org[0]
        self.cred = self.cred[0]

        if commit:
            self.org.send(self.cred)
            return self.cred
        
        return 

