from django import forms


class ImportForm(forms.Form):
    file_import = forms.FileField()


class SchemaForm(forms.Form):
    file_template = forms.FileField()
