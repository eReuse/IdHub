from django import forms


class Organization(forms.Form):
    wallet = forms.ChoiceField(
        "Wallet",
        choices=[(x.id, x.name) for x in Organization.objects.all()]
    )

    def clean_wallet(self):
        data = self.cleaned_data["wallet"]
        organization = Organization.objects.filter(
            id=data
        )

        if not organization.exists():
            raise ValidationError("organization is not valid!")

        self.organization = organization.first()
            
        return data

    def authorize(self):
        data = {
            "response_type": "vp_token",
            "response_mode": "direct_post",
            "client_id": self.organization.client_id,
            "response_uri": settings.RESPONSE_URI,
            "presentation_definition": self.pv_definition(),
            "nonce": ""
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(data)

        url = '{response_uri}/authorize?{params}'.format(
            response_uri=self.organization.response_uri,
            params=query_dict.urlencode()
        )

    def pv_definition(self):
        return ""
