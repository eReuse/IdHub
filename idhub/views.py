import logging
import datetime
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
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
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User

from .forms import LoginForm


logger = logging.getLogger(__name__)



class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "idhub/user_dashboard.html"
    title = _('Dashboard')
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.title,
        })
        return context


class AdminDashboardView(UserDashboardView):
    template_name = "idhub/admin_dashboard.html"


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
