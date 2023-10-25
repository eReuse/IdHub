from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy, resolve
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect


class UserView(LoginRequiredMixin):
    login_url = "/login/"
    wallet = False

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
        })
        return context


class AdminView(UserView):

    def get(self, request, *args, **kwargs):
        if not request.user.is_admin:
            url = reverse_lazy('idhub:user_dashboard')
            return redirect(url)

        return super().get(request, *args, **kwargs)
