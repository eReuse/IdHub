from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import views as auth_views
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy, resolve
from django.shortcuts import redirect
from django.core.cache import cache


class Http403(PermissionDenied):
    status_code = 403
    default_detail = _('Permission denied. User is not authenticated')
    default_code = 'forbidden'

    def __init__(self, detail=None, code=None):
        if detail is not None:
            self.detail = details or self.default_details
        if code is not None:
            self.code = code or self.default_code


class UserView(LoginRequiredMixin):
    login_url = "/login/"
    wallet = False
    path_terms = [
        'admin_terms_and_conditions',
        'user_terms_and_conditions',
        'user_gdpr',
    ]

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        url = self.check_gdpr()
        if url:
            return url

        return response
        
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        url = self.check_gdpr()
        if url:
            return url

        return response

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

    def check_gdpr(self):
        if not self.request.user.accept_gdpr:
            url = reverse_lazy("idhub:user_terms_and_conditions")
            if self.request.user.is_admin:
                url = reverse_lazy("idhub:admin_terms_and_conditions")
            if resolve(self.request.path).url_name not in self.path_terms:
                return redirect(url)


class AdminView(UserView):

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.check_valid_user()
        return super().post(request, *args, **kwargs)

    def check_valid_user(self):
        if not self.request.user.is_admin:
            raise Http403()

        if self.request.session.get("2fauth"):
            raise Http403()
        
