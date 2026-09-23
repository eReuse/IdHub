from django import forms
from django.utils.translation import gettext_lazy as _
from webhook.models import Token
from idhub.models import DID

class TokenForm(forms.ModelForm):
    active = forms.TypedChoiceField(
        label=_("Status"),
        choices=((True, _("Active")), (False, _("Disabled"))),
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        coerce=lambda x: x == "True" or x is True,
        initial=True,
    )

    class Meta:
        model = Token
        fields = ("label", "active", "allowed_dids")
        widgets = {
            # Switch from a dropdown list to checkboxes for intuitive multi-selection/deselection
            'allowed_dids': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['allowed_dids'].queryset = DID.objects.filter(
            user__isnull=True,
            is_product=False
        )
        self.fields['allowed_dids'].help_text = _(
            "Select the DIDs this token is permitted to use. If left blank, the token will not have access to any DIDs."
        )
        self.fields['allowed_dids'].required = False
