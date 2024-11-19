import logging

from django.conf import settings
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect
from django.http import HttpResponseRedirect


logger = logging.getLogger(__name__)


class LoginView(auth_views.LoginView):
    template_name = 'login.html'
    extra_context = {
        'title': _('Login'),
        'success_url': reverse_lazy('dashboard:unassigned_devices'),
        'commit_id': settings.COMMIT,
    }

    def get(self, request, *args, **kwargs):
        self.extra_context['success_url'] = request.GET.get(
            'next',
            reverse_lazy('dashboard:unassigned_devices')
        )
        if not self.request.user.is_anonymous:
            return redirect(reverse_lazy('dashboard:unassigned_devices'))
            
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        auth_login(self.request, user)

        if user.is_anonymous:
            return redirect(reverse_lazy("login:login"))

        return redirect(self.extra_context['success_url'])


def LogoutView(request):
    auth_logout(request)
    return redirect(reverse_lazy("login:login"))


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'password_reset_confirm.html'
    success_url = reverse_lazy('login:password_reset_complete')

    def form_valid(self, form):
        password = form.cleaned_data.get("new_password1")
        user = form.user
        user.set_password(password)
        user.save()
        return HttpResponseRedirect(self.success_url)


class PasswordResetView(auth_views.PasswordResetView):
    template_name = 'password_reset.html'
    email_template_name = 'password_reset_email.txt'
    html_email_template_name = 'password_reset_email.html'
    subject_template_name = 'password_reset_subject.txt'
    success_url = reverse_lazy('login:password_reset_done')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            return response
        except Exception as err:
            logger.error(err)
        return HttpResponseRedirect(self.success_url)

