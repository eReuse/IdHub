from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import views as auth_views


class LoginView(auth_views.LoginView):
    template_name = 'auth/login.html'
    extra_context = {
        'title': _('Login'),
        'success_url': reverse_lazy('idhub:user_dashboard'),
    }

    def get(self, request):
        if request.GET.get('next'):
            self.extra_context['success_url'] = request.GET.get('next')
        return super().get(request)
