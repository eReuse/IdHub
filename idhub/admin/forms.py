from django import forms


class ImportForm(forms.Form):
    file_import = forms.FileField()
