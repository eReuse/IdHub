from django import forms
from idhub_auth.models import User
from idhub.models import DID, VerificableCredential


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
            id=self.data['credential']
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

