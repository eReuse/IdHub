from django import forms
from django.utils.translation import gettext_lazy as _
from webhook.models import Token
from idhub.models import DID

class TokenCreateForm(forms.ModelForm):
    class Meta:
        model = Token
        fields = ("label", "allowed_dids")
        widgets = {
            'allowed_dids': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['allowed_dids'].queryset = DID.objects.filter(
            user__isnull=True, is_product=False
        )
        self.fields['allowed_dids'].help_text = _(
            "Select the DIDs this token is permitted to use."
        )
        self.fields['allowed_dids'].required = False


class TokenUpdateForm(TokenCreateForm):
    active = forms.ChoiceField(
        label=_("Status"),
        choices=(("1", _("Active")), ("0", _("Disabled"))),
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )

    class Meta(TokenCreateForm.Meta):
        fields = ("label", "active", "allowed_dids")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['active'] = "1" if self.instance.active else "0"

    def clean_active(self):
        return self.cleaned_data.get('active') == "1"
