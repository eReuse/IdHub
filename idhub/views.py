import logging
import datetime
import json

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import DeleteView, FormView
from django.views.generic.list import ListView
from django.contrib.auth.models import User

from .forms import LoginForm


logger = logging.getLogger(__name__)



class UserDashboardView(TemplateView):
    template_name = "idhub/user_dashboard.html"
    extra_context = {
        'title': _('Dashboard'),
    }


class LoginView(FormView):
    template_name = 'auth/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('dashboard')
    extra_context = {
        'title': _('Login'),
    }

    def form_valid(self, form):
        return self.success_url


class LogoutView(RedirectView):
    """
    Log out the user.
    """
    permanent = False
    pattern_name = 'login'

    def get_redirect_url(self, *args, **kwargs):
        """
        Logs out the user.
        """
        return super().get_redirect_url(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Logout may be done via POST."""
        return self.get(request, *args, **kwargs)
