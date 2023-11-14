import csv
import json
import copy
import pandas as pd
from jsonschema import validate

from django import forms
from django.core.exceptions import ValidationError
from idhub.models import (
    DID,
    File_datas, 
    Schemas,
    VerificableCredential,
)
from idhub_auth.models import User


class ImportForm(forms.Form):
    did = forms.ChoiceField(choices=[])
    schema = forms.ChoiceField(choices=[])
    file_import = forms.FileField()

    def __init__(self, *args, **kwargs):
        self._schema = None
        self._did = None
        self.rows = {}
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['did'].choices = [
            (x.did, x.label) for x in DID.objects.filter(user=self.user)
        ]
        self.fields['schema'].choices = [
            (x.id, x.name()) for x in Schemas.objects.filter()
        ]

    def clean_did(self):
        data = self.cleaned_data["did"]
        did = DID.objects.filter(
            user=self.user,
            did=data
        )

        if not did.exists():
            raise ValidationError("Did is not valid!")

        self._did = did.first()
            
        return data

    def clean_schema(self):
        data = self.cleaned_data["schema"]
        schema = Schemas.objects.filter(
            id=data
        )
        if not schema.exists():
            raise ValidationError("Schema is not valid!")

        self._schema = schema.first()

        return data

    def clean_file_import(self):
        data = self.cleaned_data["file_import"]
        self.file_name = data.name
        if File_datas.objects.filter(file_name=self.file_name, success=True).exists():
            raise ValidationError("This file already exists!")

        self.json_schema = json.loads(self._schema.data)
        df = pd.read_csv (data, delimiter="\t", quotechar='"', quoting=csv.QUOTE_ALL)
        data_pd = df.fillna('').to_dict()

        if not data_pd:
            self.exception("This file is empty!")

        for n in range(df.last_valid_index()+1):
            row = {}
            for k in data_pd.keys():
                row[k] = data_pd[k][n]

            user = self.validate_jsonld(n, row)
            self.rows[user] = row

        return data

    def save(self, commit=True):
        table = []
        for k, v in self.rows.items():
            table.append(self.create_credential(k, v)) 

        if commit:
            for cred in table:
              cred.save()
            File_datas.objects.create(file_name=self.file_name)
            return table
        
        return 

    def validate_jsonld(self, line, row):
        try:
            validate(instance=row, schema=self.json_schema)
        except Exception as e:
            msg = "line {}: {}".format(line+1, e)
            self.exception(msg)

        user = User.objects.filter(email=row.get('email'))
        if not user:
            txt = _('The user not exist!')
            msg = "line {}: {}".format(line+1, txt)
            self.exception(msg)

        return user.first()

    def create_credential(self, user, row):
        d = copy.copy(self.json_schema)
        d['instance'] = row
        return VerificableCredential(
            verified=False,
            user=user,
            data=json.dumps(d)
        )

    def exception(self, msg):
        File_datas.objects.create(file_name=self.file_name, success=False)
        raise ValidationError(msg)


class SchemaForm(forms.Form):
    file_template = forms.FileField()
