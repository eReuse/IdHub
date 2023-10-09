from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy, resolve
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.shortcuts import redirect


class UserView(LoginRequiredMixin, TemplateView):
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.title,
            'subtitle': self.subtitle,
            'icon': self.icon,
            'section': self.section,
            'path': resolve(self.request.path).url_name,
            'user': self.request.user
        })
        return context


class AdminView(UserView):

    def get(self, request):
        if not request.user.is_superuser:
            url = reverse_lazy('idhub:user_dashboard')
            return redirect(url)

        return super().get(request)
