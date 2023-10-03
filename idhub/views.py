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
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .models import AppUser
from .forms import UserForm
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

from .forms import LoginForm


logger = logging.getLogger(__name__)


def index(request):
    return redirect("/user")


@login_required
def user(request):
    current_user: AppUser = request.user.appuser
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            cdata = form.cleaned_data
            current_user.django_user.first_name = cdata['first_name']
            current_user.save()
            current_user.django_user.save()
            return HttpResponseRedirect(reverse("user"))
        else:
            return render(request, "idhub/user-details.html", {"form": form})
    elif request.method == "GET":
        form = UserForm.from_user(current_user)
        return render(request, "idhub/user-details.html", {"form": form})


# class UserDashboardView(LoginRequiredMixin, TemplateView):
class UserDashboardView(TemplateView):
    template_name = "idhub/user_dashboard.html"
    title = _('Dashboard')
    #login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.title,
        })
        return context


class LoginView(FormView):
    template_name = 'auth/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('idhub:user_dashboard')
    extra_context = {
        'title': _('Login'),
    }

    def form_valid(self, form):
        return super().form_valid(form)


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
