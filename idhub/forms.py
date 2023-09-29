from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate


class LoginForm(AuthenticationForm):

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if not (username and password):
            raise self.get_invalid_login_error()

        user = authenticate(username=username, password=password)

        if user is not None:
            raise self.get_invalid_login_error()

        return self.cleaned_data

