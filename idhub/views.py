from django.urls import reverse_lazy
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import views as auth_views
from django.contrib.auth import login as auth_login
from django.http import HttpResponseRedirect


class LoginView(auth_views.LoginView):
    template_name = 'auth/login.html'
    extra_context = {
        'title': _('Login'),
        'success_url': reverse_lazy('idhub:user_dashboard'),
    }

    def get(self, request, *args, **kwargs):
        self.extra_context['success_url'] = request.GET.get(
            'next',
            reverse_lazy('idhub:user_dashboard')
        )
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        password = form.cleaned_data.get("password")
        auth_login(self.request, user)

        sensitive_data_encryption_key = user.decrypt_sensitive_data(password)

        if not user.is_anonymous and user.is_admin:
            admin_dashboard = reverse_lazy('idhub:admin_dashboard')
            self.extra_context['success_url'] = admin_dashboard
            cache.set("KEY_DIDS", sensitive_data_encryption_key, None)

        self.request.session["key_did"] = user.encrypt_data(
            sensitive_data_encryption_key,
            user.password+self.request.session._session_key
        )

        return HttpResponseRedirect(self.extra_context['success_url'])


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('idhub:password_reset_complete')

    def form_valid(self, form):
        password = form.cleaned_data.get("password")
        user = form.get_user()
        user.set_encrypted_sensitive_data(password)
        user.save()
        return HttpResponseRedirect(self.success_url)
