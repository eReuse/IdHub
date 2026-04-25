#!/usr/bin/env python3
from django import forms
from django.utils.translation import gettext_lazy as _


class VerificationForm(forms.Form):
    file_import = forms.FileField(
        widget=forms.FileInput(attrs={'id': 'file-input', 'style': 'display:none;'})
    )
