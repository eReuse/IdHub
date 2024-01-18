from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy, resolve
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect
from django.core.cache import cache


class UserView(LoginRequiredMixin):
    login_url = "/login/"
    wallet = False

    def get(self, request, *args, **kwargs):
        self.admin_validated = cache.get("KEY_DIDS")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.admin_validated = cache.get("KEY_DIDS")
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.title,
            'subtitle': self.subtitle,
            'icon': self.icon,
            'section': self.section,
            'path': resolve(self.request.path).url_name,
            'user': self.request.user,
            'wallet': self.wallet,
            'admin_validated': True if self.admin_validated else False
        })
        return context


class AdminView(UserView):

    def get(self, request, *args, **kwargs):
        if not request.user.is_admin:
            url = reverse_lazy('idhub:user_dashboard')
            return redirect(url)

        return super().get(request, *args, **kwargs)
