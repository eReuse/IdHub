from django import forms
from idhub_auth.models import User
from idhub.models import DID, VerificableCredential, Organization



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
        cred.get_issued(did)

        if commit:
            cred.save()
            return cred
        
        return 



class CredentialPresentationForm(forms.Form):
    organization = forms.ChoiceField(choices=[])
    credential = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['organization'].choices = [
            (x.id, x.name) for x in Organization.objects.filter()
        ]
        self.fields['credential'].choices = [
            (x.id, x.type()) for x in VerificableCredential.objects.filter(
                user=self.user,
                status=VerificableCredential.Status.ISSUED
            )
        ]

    def save(self, commit=True):
        org = Organization.objects.filter(
            id=self.data['organization']
        )
        cred = VerificableCredential.objects.filter(
            user=self.user,
            id=self.data['credential'],
            status=VerificableCredential.Status.ISSUED
        )
        if not all([org.exists(), cred.exists()]):
            return

        org =org[0]
        cred = cred[0]

        if commit:
            org.send(cred)
            return cred
        
        return 

