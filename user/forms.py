from django import forms


class SettingsForm(forms.Form):
    token = forms.ChoiceField(
        choices = []
    )
    erasure = forms.ChoiceField(
        choices = [(0, 'Not erasure'),
            ('basic', 'Erasure Basic'),
            ('baseline', 'Erasure Baseline'),
            ('enhanced', 'Erasure Enhanced'),
        ],
    )

    def __init__(self, *args, **kwargs):
        tokens = kwargs.pop('tokens')
        super().__init__(*args, **kwargs)
        tk = [(str(x.token), x.tag) for x in tokens]
        self.fields['token'].choices = tk
