import re

from django import forms
from django.utils.translation import gettext_lazy as _
from idhub_auth.models import User


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_admin']

    def clean_first_name(self):
        first_name = super().clean()['first_name']
        match = r'^[a-zA-ZäöüßÄÖÜáéíóúàèìòùÀÈÌÒÙÁÉÍÓÚßñÑçÇ\s\'-]+'
        if not re.fullmatch(match, first_name):
            txt = _("The string must contain only characters and spaces")
            raise forms.ValidationError(txt)

        return first_name

    def clean_last_name(self):
        last_name = super().clean()['last_name']
        match = r'^[a-zA-ZäöüßÄÖÜáéíóúàèìòùÀÈÌÒÙÁÉÍÓÚßñÑçÇ\s\'-]+'
        if not re.fullmatch(match, last_name):
            txt = _("The string must contain only characters and spaces")
            raise forms.ValidationError(txt)

        return last_name

