import logging

from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.contrib import messages
from .mixins import AdminView


class AdminDashboardView(AdminView):
    template_name = "idhub/admin_dashboard.html"
    title = _('Dashboard')

