import json
import base64
import logging
import jsonschema
import requests
import pandas as pd

from nacl.exceptions import CryptoError
from openpyxl import load_workbook
from urllib.parse import urlparse, urljoin
from django.conf import settings
from django.urls import reverse
from django import forms
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from utils import certs, credtools
from idhub.models import (
    DID,
    ContextFile,
    File_datas,
    Membership,
    Schemas,
    UserRol,
    VerificableCredential,
    VCTemplatePdf,
)
from idhub_auth.models import User


logger = logging.getLogger(__name__)


class TermsConditionsForm2(forms.Form):
    accept = forms.BooleanField(
        label=_("Accept terms and conditions of the service"),
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        data = self.cleaned_data
        if data.get("accept"):
            self.user.accept_gdpr = True
        else:
            self.user.accept_gdpr = False
        return data

    def save(self, commit=True):

        if commit:
            self.user.save()
            return self.user

        return


class EncryptionKeyForm(forms.Form):
    key = forms.CharField(
        label=_("Key for encrypt the secrets of all system"),
        required=True
    )

    def clean(self):
        data = self.cleaned_data
        self._key = data["key"]
        if not DID.objects.exists():
            return data

        did = DID.objects.first()
        cache.set("KEY_DIDS", self._key, None)
        try:
            did.get_key_material()
        except CryptoError:
            cache.set("KEY_DIDS", None)
            txt = _("Key no valid!")
            raise ValidationError(txt)

        cache.set("KEY_DIDS", None)
        return data

    def save(self, commit=True):

        if commit:
            cache.set("KEY_DIDS", self._key, None)
            if not DID.objects.exists():
                did = DID.objects.create(label='Default', type=DID.Types.WEB)
                did.set_did()
                did.save()

        return


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
        label += f' <a class="btn btn-green-admin" target="_blank" href="{url}" '
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


class ImportSchemaForm(forms.Form):
    schema_import = forms.FileField(label=_("Schema to import"))
    context_import = forms.FileField(label=_("Context to import (optional)"), required=False)

    def clean(self):
        data = self.cleaned_data["schema_import"]
        context = self.cleaned_data["context_import"]
        self.context = {}

        try:
            self.file_name = data.name
            self.schema = json.loads(data.read())
        except Exception:
             raise ValidationError(_("This schema not is a json file"))

        if context and ContextFile.objects.filter(file_name=context.name).exists():
            raise ValidationError(_("This context exist"))

        try:
            self.context["file_name"] = context.name
            self.context["data"] = context.read()
        except Exception:
            pass

        try:
            if context:
                self.context["data"] = json.dumps(json.loads(self.context["data"]))
        except Exception:
            raise ValidationError(_("This context is no a valid jsonld"))

        try:
            assert credtools.validate_schema(self.schema)
            assert self.schema.get('name')
            assert self.schema.get('title')
        except Exception:
            raise ValidationError(_("This is not a valid schema!"))

        if Schemas.objects.filter(file_schema=self.file_name).exists():
            raise ValidationError(_("Schema exist!"))

        return data

    def save(self, domain=None, commit=True):
        _name = json.dumps(self.schema.get("name"))
        _description = json.dumps(self.schema.get("description"))
        title = self.schema.get("title")
        data = json.dumps(self.schema)
        url_context = None

        if self.context and domain:
            file_name = self.context["file_name"]
            url_context = urljoin(domain, reverse("idhub:context_file", args=[file_name]))

        schema = Schemas.objects.create(
            file_schema=self.file_name,
            data=data,
            _name=_name,
            _description=_description,
            type=title,
            template_description=_description,
            context=url_context
        )

        if url_context:
            ContextFile.objects.create(schema=schema, **self.context)

        return schema


class ImportSchemaUrlForm(forms.Form):
    schema = forms.CharField(label=_("Schema url reference"))
    context = forms.CharField(label=_("Context url reference"))

    def clean(self):
        schema = self.cleaned_data["schema"]
        self.context = self.cleaned_data["context"]

        try:
            path= urlparse(schema).path
            self.file_name = path.split("/")[-1]
            if self.file_name[-5:] != ".json":
                self.file_name += ".json"
            self.schema = requests.get(schema).json()
        except Exception:
             raise ValidationError(_("This schema not is a json file"))

        try:
            res = requests.get(self.context)
            assert 200 <= res.status_code < 300
            res.json()
        except Exception:
             raise ValidationError(_("This context is not accessible"))

        try:
            assert credtools.validate_schema(self.schema)
            assert self.schema.get('name')
            assert self.schema.get('title')
        except Exception:
            raise ValidationError(_("This is not a valid schema!"))

        if Schemas.objects.filter(_name=self.schema["name"]).exists():
            raise ValidationError(_("Schema exist!"))

        return self.cleaned_data

    def save(self):
        _name = json.dumps(self.schema.get("name"))
        _description = json.dumps(self.schema.get("description"))
        title = self.schema.get("title")
        data = json.dumps(self.schema)
        schema = Schemas.objects.create(
            file_schema=self.file_name,
            data=data,
            _name=_name,
            _description=_description,
            type=title,
            template_description=_description,
            context=self.context
        )

        return schema


class ImportForm(forms.Form):
    did = forms.ChoiceField(label=_("Did"), choices=[])
    eidas1 = forms.ChoiceField(
        label=_("Signature with Eidas1"),
        choices=[],
        required=False
    )
    template_pdf = forms.ChoiceField(
        label=_("Select one template for render to Pdf"),
        choices=[],
        required=False
    )
    schema = forms.ChoiceField(label=_("Schema"), choices=[])
    file_import = forms.FileField(label=_("File to import"))

    def __init__(self, *args, **kwargs):
        self._schema = None
        self._did = None
        self._eidas1 = None
        self.rows = {}
        self.properties = {}
        self.users = []
        super().__init__(*args, **kwargs)
        dids = DID.objects.filter(user__isnull=True)
        self.fields['did'].choices = [
            (x.did, x.label) for x in dids.filter(eidas1=False)
        ]
        txt_select_one = _("Please choose a data schema ...")
        self.fields['schema'].choices = [(0,txt_select_one)] + [
            (x.id, x.name) for x in Schemas.objects.filter()
        ]

        if dids.filter(eidas1=True).exists():
            choices = [("", "")]
            choices.extend([
                (x.did, x.label) for x in dids.filter(eidas1=True)
            ])
            self.fields['eidas1'].choices = choices
        else:
          self.fields.pop('eidas1')

        if self.fields.get('eidas1') and VCTemplatePdf.objects.filter().exists():
            choices = [("", "")]
            choices.extend([
                (x.id, x.name) for x in VCTemplatePdf.objects.all()
            ])
            self.fields['template_pdf'].choices = choices
        else:
          self.fields.pop('template_pdf')

    def clean(self):
        data = self.cleaned_data["did"]
        did = DID.objects.filter(
            user__isnull=True,
            did=data
        )

        if not did.exists():
            raise ValidationError(_("Did not valid!"))

        self._did = did.first()

        eidas1 = self.cleaned_data.get('eidas1')
        if eidas1:
            self._eidas1 = DID.objects.filter(
                user__isnull=True,
                eidas1=True,
                did=eidas1
            ).first()

        template_pdf = self.cleaned_data.get('template_pdf')
        self._template_pdf = None
        if template_pdf and eidas1:
            self._template_pdf = VCTemplatePdf.objects.filter(
                id=template_pdf
            ).first()

        return data

    def clean_schema(self):
        data = self.cleaned_data["schema"]
        schema = Schemas.objects.filter(
            id=data
        )
        if not schema.exists():
            raise ValidationError(_("Schema is not valid!"))

        self._schema = schema.first()
        try:
            self.json_schema = self._schema.get_credential_subject_schema()
        except Exception:
            raise ValidationError(_("Schema not valid!"))

        return data

    def clean_file_import(self):
        data = self.cleaned_data["file_import"]
        if not self._schema:
            return data

        self.file_name = data.name
        props = self.json_schema.get("properties", {})

        # Forze than pandas read one column as string
        dtype_dict = {
            "phoneNumber": str,
            "phone": str,
            'postCode': str
        }
        try:
            df = pd.read_excel(data, dtype=dtype_dict)
            df.fillna('', inplace=True)
        except Exception:
            txt = _("This file does not a excel valid!")
            raise ValidationError(txt)

        try:
            workbook = load_workbook(data)
            # if no there are schema meen than is a excel costum and you
            # don't have control abour that
            if 'Schema' in workbook.custom_doc_props.names:
                excel_schema = workbook.custom_doc_props['Schema'].value
                file_schema = self._schema.file_schema.split('.json')[0]
                assert file_schema in excel_schema
        except Exception:
            txt = _("This File does not correspond to this scheme!")
            raise ValidationError(txt)

        # convert dates to iso 8601
        for col in df.select_dtypes(include='datetime').columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d")
        df.fillna('', inplace=True)

        # convert numbers to strings if this is indicate in schema
        for col in props.keys():
            if col not in df.columns:
                continue

            if "string" in props[col]["type"]:
                df[col] = df[col].astype(str)

            # TODO @cayop if there are a cel with nan then now is ''
            # for this raison crash with df[col].astype(int)
            # elif "integer" in props[col]["type"]:
            #     df[col] = df[col].astype(int)

            # elif "number" in props[col]["type"]:
            #     df[col] = df[col].astype(float)

        data_pd = df.to_dict(orient='index')

        if not data_pd or df.last_valid_index() is None:
            self.exception(_("The file you try to import is empty!"))

        for n in data_pd.keys():
            row = {}
            d = data_pd[n]
            for k, v in d.items():
                if d[k] or d[k] == 0:
                    row[k] = d[k]

            if row:
                user = self.validate_jsonld(n+2, row)
                if user:
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
            jsonschema.validate(
                instance=row,
                schema=self.json_schema,
                format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
            )
        except jsonschema.exceptions.ValidationError as err:
            msg = "line {}: {}".format(line, err.message)
            self.exception(msg)

        user, new = User.objects.get_or_create(email=row.get('email'))
        if new:
            self.users.append(user)
            user.set_encrypted_sensitive_data()
            user.save()
            self.create_defaults_dids(user)

        return user

    def create_defaults_dids(self, user):
        did = DID(label="Default", user=user, type=DID.Types.WEB)
        did.set_did()
        did.save()

    def create_credential(self, user, row):
        bcred = VerificableCredential.objects.filter(
            user=user,
            schema=self._schema,
            issuer_did=self._did,
            status=VerificableCredential.Status.ENABLED
        )
        if bcred.exists():
            cred = bcred.first()
            cred.csv_data = json.dumps(row, default=str)
            cred.eidas1_did = self._eidas1
            cred.template_pdf = self._template_pdf
            return cred

        cred = VerificableCredential(
            verified=False,
            user=user,
            csv_data=json.dumps(row, default=str),
            issuer_did=self._did,
            schema=self._schema,
            eidas1_did=self._eidas1,
            template_pdf=self._template_pdf
        )
        cred.set_type()
        return cred

    def exception(self, msg):
        File_datas.objects.create(file_name=self.file_name, success=False)
        raise ValidationError(msg)


class SchemaForm(forms.Form):
    file_template = forms.FileField(label=_("File template"))


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

        if members.filter(start_date__lte=start_date, end_date=None).exists():
            msg = _("This membership already exists!")
            raise forms.ValidationError(msg)

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

        if not end_date:
            members = members.filter(
                start_date__gte=start_date,
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


class ImportCertificateForm(forms.Form):
    label = forms.CharField(label=_("Label"))
    password = forms.CharField(
        label=_("Password of certificate"),
        widget=forms.PasswordInput
    )
    file_import = forms.FileField(label=_("File import"))

    def __init__(self, *args, **kwargs):
        self._did = None
        self._s = None
        self._label = None
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        file_import = data.get('file_import')
        self.pfx_file = file_import.read()
        self.file_name = file_import.name
        self._pss = data.get('password')
        self._label = data.get('label')
        if not self.pfx_file or not self._pss:
            msg = _("Is not a valid certificate")
            raise forms.ValidationError(msg)

        self.signer_init()
        if not self._s:
            msg = _("Is not a valid certificate")
            raise forms.ValidationError(msg)

        self.new_did()
        return data

    def new_did(self):
        keys = {
            "cert": base64.b64encode(self.pfx_file).decode('utf-8'),
            "passphrase": self._pss
        }
        key_material = json.dumps(keys)
        self._did = DID(
            key_material=key_material,
            did=self.file_name,
            label=self._label,
            eidas1=True,
            type=DID.Types.KEY
        )

        self._did.set_key_material(key_material)

    def save(self, commit=True):

        if commit:
            self._did.save()
            return self._did

        return

    def signer_init(self):
        self._s = certs.load_cert(
            self.pfx_file, self._pss.encode('utf-8')
        )
