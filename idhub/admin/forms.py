from django import forms
from django.contrib.auth.models import User


class ProfileForm(forms.ModelForm):
    MANDATORY_FIELDS = ['first_name', 'last_name', 'email', 'username']

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


class MembershipForm(forms.ModelForm):
    MANDATORY_FIELDS = ['type']


class RolForm(forms.ModelForm):
    MANDATORY_FIELDS = ['name']


class ServiceForm(forms.ModelForm):
    MANDATORY_FIELDS = ['domain', 'rol']

