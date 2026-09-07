from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import os

class VerificationForm(forms.Form):
    # limits data to 5mb
    MAX_UPLOAD_SIZE = 5242880

    ALLOWED_CONTENT_TYPES = [
        'application/json',
        'application/ld+json',
        'application/pdf',
        'application/jwt',
        'application/vc+jwt',
    ]

    ALLOWED_EXTENSIONS = ['.json', '.pdf', '.jwt']

    file_import = forms.FileField(
        label=_("Credential File"),
        help_text=_("Upload a Verifiable Credential file (JSON, PDF, or JWT). Maximum size: 5MB."),
        widget=forms.FileInput(attrs={
            'id': 'file-input',
            'style': 'display:none;',
            'accept': '.json, .pdf, .jwt, application/json, application/jwt'
        })
    )

    def clean_file_import(self):
        file = self.cleaned_data.get('file_import')

        if not file:
            return file

        if file.size > self.MAX_UPLOAD_SIZE:
            raise ValidationError(
                _("The file is too large. The maximum allowed size is 5MB.")
            )

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValidationError(
                _("Invalid file extension. Only .json, .pdf and .jwt are allowed.")
            )

        generic_mimes = ['application/octet-stream', 'text/plain', '']

        if file.content_type not in self.ALLOWED_CONTENT_TYPES and file.content_type not in generic_mimes:
            raise ValidationError(
                _("Unsupported file format. Please upload a valid JSON, PDF, or JWT credential.")
            )

        if ext in ['.json', '.jwt']:
            try:
                file.read().decode('utf-8')
                file.seek(0)
            except UnicodeDecodeError:
                raise ValidationError(_("The file is not a valid UTF-8 encoded text file."))

        return file
