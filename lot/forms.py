from django import forms
from lot.models import Lot


class LotsForm(forms.Form):
    lots = forms.ModelMultipleChoiceField(
        queryset=Lot.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self):
        self._lots = self.cleaned_data.get("lots")
        return self._lots
    
    def save(self, commit=True):
        if not commit:
            return

        for dev in self.devices:
            for lot in self._lots:
                lot.add(dev.id)
        return

    def remove(self):
        for dev in self.devices:
            for lot in self._lots:
                lot.remove(dev.id)
        return
