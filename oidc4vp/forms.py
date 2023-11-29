from django import forms
from django.conf import settings

from oidc4vp.models import Organization


# class OrganizationForm(forms.Form):
#     wallet = forms.ChoiceField(
#         "Wallet",
#         choices=[(x.id, x.name) for x in Organization.objects.all()]
#     )

#     def clean_wallet(self):
#         data = self.cleaned_data["wallet"]
#         organization = Organization.objects.filter(
#             id=data
#         )

#         if not organization.exists():
#             raise ValidationError("organization is not valid!")

#         self.organization = organization.first()
            
#         return data

#     def authorize(self):
#         data = {
#             "response_type": "vp_token",
#             "response_mode": "direct_post",
#             "client_id": self.organization.client_id,
#             "response_uri": settings.RESPONSE_URI,
#             "presentation_definition": self.pv_definition(),
#             "nonce": ""
#         }
#         query_dict = QueryDict('', mutable=True)
#         query_dict.update(data)

#         url = '{response_uri}/authorize?{params}'.format(
#             response_uri=self.organization.response_uri,
#             params=query_dict.urlencode()
#         )

#     def pv_definition(self):
#         return ""


class AuthorizeForm(forms.Form):
    organization = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        # import pdb; pdb.set_trace()
        self.user = kwargs.pop('user', None)
        self.presentation_definition = kwargs.pop('presentation_definition', [])
        self.credentials = self.user.vcredentials.filter(
            schema__type__in=self.presentation_definition
        )
        super().__init__(*args, **kwargs)
        self.fields['organization'].choices = [
            (x.id, x.name) for x in Organization.objects.filter() 
                if x.response_uri != settings.RESPONSE_URI
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

