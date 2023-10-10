from django import forms
from django.contrib.auth.models import User


class ProfileForm(form.ModelForm):
    MANDATORY_FIELDS = ['first_name', 'last_name', 'email']
    OPTIONAL_FIELDS = []

    class Meta:
        model = User
        fields = ('forst_name', 'last_name', 'email')