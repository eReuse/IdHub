from django.urls import reverse_lazy
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import views as auth_views
from django.contrib.auth import login as auth_login
from django.http import HttpResponseRedirect
from nacl import secret


class LoginView(auth_views.LoginView):
    template_name = 'auth/login.html'
    extra_context = {
        'title': _('Login'),
        'success_url': reverse_lazy('idhub:user_dashboard'),
    }

    def get(self, request, *args, **kwargs):
        if request.GET.get('next'):
            self.extra_context['success_url'] = request.GET.get('next')
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_anonymous and user.is_admin:
            user_dashboard = reverse_lazy('idhub:user_dashboard')
            admin_dashboard = reverse_lazy('idhub:admin_dashboard')
            if self.extra_context['success_url'] == user_dashboard:
                self.extra_context['success_url'] = admin_dashboard

        auth_login(self.request, user)
        # Decrypt the user's sensitive data encryption key and store it in the session.
        password = form.cleaned_data.get("password")
        sensitive_data_encryption_key = user.decrypt_sensitive_data_encryption_key(password)
        key_dids = cache.get("KEY_DIDS", {})
        key_dids[user.id] = sensitive_data_encryption_key
        cache.set("KEY_DIDS", key_dids, None)

        return HttpResponseRedirect(self.extra_context['success_url'])

