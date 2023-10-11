from django import forms
from django.contrib.auth.models import User


class ProfileForm(forms.ModelForm):
    MANDATORY_FIELDS = ['first_name', 'last_name', 'email']

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')