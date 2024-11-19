from decouple import config
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from dashboard.mixins import DashboardView
from django.views.generic.edit import (
    FormView,
)

from user.forms import SettingsForm
from api.models import Token


class PanelView(DashboardView, TemplateView):
    template_name = "panel.html"
    title = _("User")
    breadcrumb = "User / Panel"
    subtitle = "User panel"

    
class SettingsView(DashboardView, FormView):
    template_name = "settings.html"
    title = _("Download Settings")
    breadcrumb = "user / workbench / settings"
    form_class = SettingsForm

    def form_valid(self, form):
        cleaned_data = form.cleaned_data.copy()
        settings_tmpl = "settings.ini"
        path = reverse("api:new_snapshot")
        cleaned_data['url'] = self.request.build_absolute_uri(path)
        
        if config("LEGACY", False):
            cleaned_data['token'] = config.get('TOKEN_LEGACY', '')
            cleaned_data['url'] = config.get('URL_LEGACY', '')
            settings_tmpl = "settings_legacy.ini"
            
        data = render(self.request, settings_tmpl, cleaned_data)
        response = HttpResponse(data.content, content_type="application/text")
        response['Content-Disposition'] = 'attachment; filename={}'.format("settings.ini")
        return response
    
    def get_form_kwargs(self):
        tokens = Token.objects.filter(owner=self.request.user)
        kwargs = super().get_form_kwargs()
        kwargs['tokens'] = tokens
        return kwargs

