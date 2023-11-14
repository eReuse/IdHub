import csv
import json
import pandas as pd
from jsonschema import validate

from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from idhub.models import (
    DID,
    File_datas,
    Membership,
    Schemas,
    Service,
    UserRol,
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
            txt = _('The user does not exist!')
            msg = "line {}: {}".format(line+1, txt)
            self.exception(msg)

        return user.first()

    def create_credential(self, user, row):
        return VerificableCredential(
            verified=False,
            user=user,
            csv_data=json.dumps(row),
            did_issuer=self._did.did,
            schema=self._schema,
        )

    def exception(self, msg):
        File_datas.objects.create(file_name=self.file_name, success=False)
        raise ValidationError(msg)


class SchemaForm(forms.Form):
    file_template = forms.FileField()

    
class MembershipForm(forms.ModelForm):

    class Meta:
        model = Membership
        fields = ['type', 'start_date', 'end_date']

    def clean_end_date(self):
        data = super().clean()
        start_date = data['start_date']
        end_date = data.get('end_date')
        members = Membership.objects.filter(
            type=data['type'],
            user=self.instance.user
        )
        if self.instance.id:
            members = members.exclude(id=self.instance.id)

        if (start_date and end_date):
            if start_date > end_date:
                msg = _("The end date is less than the start date")
                raise forms.ValidationError(msg)

            members = members.filter(
                start_date__lte=end_date,
                end_date__gte=start_date,
            )

            if members.exists():
                msg = _("This membership already exists!")
                raise forms.ValidationError(msg)
        
        return end_date


class UserRolForm(forms.ModelForm):

    class Meta:
        model = UserRol
        fields = ['service']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.id:
            user = self.instance.user
            choices = self.fields['service'].choices
            choices.queryset = choices.queryset.exclude(users__user=user)
            self.fields['service'].choices = choices
    
    def clean_service(self):
        data = super().clean()
        service = UserRol.objects.filter(
            service=data['service'],
            user=self.instance.user
        )

        if service.exists():
            msg = _("Is not possible to have a duplicate role")
            raise forms.ValidationError(msg)

        return data['service']
