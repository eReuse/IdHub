import logging

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from idhub.models import DID, VerificableCredential
from oidc4vp.models import Organization
from idhub_auth.models import User
from utils.sanitize_did import sanitize_didweb


logger = logging.getLogger(__name__)


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
        url = settings.POLICY_PRIVACY
        read = _("Privacy policy")
        return self.get_label(url, read)

    def legal_label(self):
        url = settings.POLICY_LEGAL
        read = _("Legal policy")
        return self.get_label(url, read)

    def cookies_label(self):
        url = settings.POLICY_COOKIES
        read = _("Cookies policy")
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
        self.if_credentials = kwargs.pop('if_credentials', None)
        super().__init__(*args, **kwargs)
        self.fields['did'].choices = [
            (x.did, x.label) for x in DID.objects.filter(user=self.user, available=True)
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
        ).first()
        cred = VerificableCredential.objects.filter(
            user=self.user,
            id=self.data['credential'],
            status=VerificableCredential.Status.ENABLED
        ).first()

        if not all([cred, did]):
            return

        if commit and self._domain:
            cred.issue(did, domain=self._domain)

            # TODO checkbox "publish inmediately to DLT"
            #if did.type == DID.Types.WEBETH:
            #    cred.call_oracle()

            cred.save()
            return cred

        return


class DemandAuthorizationForm(forms.Form):
    organization = forms.ChoiceField(label=_("Organization"), choices=[])

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.if_credentials = kwargs.pop('if_credentials', None)
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

        if commit:
            url = self.org.demand_authorization()
            if url.status_code == 200:
                return url.json().get('redirect_uri')

        return


class DIDForm(forms.ModelForm):
    class Meta:
        model = DID
        fields = ['label', 'type', 'did']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        data = self.cleaned_data
        label = data.get("label")
        typ = DID.Types(int(data.get("type")))
        self._did = data.get("did").lower()

        if typ in [DID.Types.WEB, DID.Types.WEBETH]:
            self._did = sanitize_didweb(self._did)

        if DID.objects.filter(did=self._did).first():
            raise ValidationError(_("This DID exist already"))

        if DID.objects.filter(label=label, user=self.user).first():
            raise ValidationError(_("This Label exist already"))

        if not self.instance.is_web:
            self.instance = DID(
                user=self.user,
                type=typ,
                label=label
            )
            return data

        self.instance.label = label
        if self.instance.did != self._did:
            self.instance.did = self._did
            self.instance.get_did_document()
            if settings.DOMAIN != self._did.split(":")[2]:
                self.instance.available = False

        return data

    def save(self, commit=True):

        self.instance.did = self._did
        if not self.instance.is_web:
            self.instance.set_did()

        if commit:
            self.instance.save()
            return self.instance

        return
