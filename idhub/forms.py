from django import forms
from .models import AppUser


class UserForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField()
    date_joined = forms.DateField()

    # Extra data:
    afiliacio = forms.CharField()

    @classmethod
    def from_user(cls, user: AppUser):
        d = {
            "first_name": user.django_user.first_name,
            "last_name": user.django_user.last_name,
            "email": user.django_user.email,
            "date_joined": user.django_user.date_joined,

            "afiliacio": "lareputa"
        }
        return cls(d)
