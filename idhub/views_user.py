import logging

from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.contrib import messages
from .mixins import UserView


class UserDashboardView(UserView):
    template_name = "idhub/user_dashboard.html"
    title = _('Dashboard')

