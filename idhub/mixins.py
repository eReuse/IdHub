from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy, resolve
from django.shortcuts import redirect
from django.core.cache import cache
from django.conf import settings


class Http403(PermissionDenied):
    status_code = 403
    default_detail = _('Permission denied. User is not authenticated')
    default_code = 'forbidden'

    def __init__(self, details=None, code=None):
        if details is not None:
            self.detail = details or self.default_details
        if code is not None:
            self.code = code or self.default_code


class UserView(LoginRequiredMixin):
    login_url = "/login/"
    wallet = False
    admin_validated = False
    path_terms = [
        'admin_terms_and_conditions',
        'user_terms_and_conditions',
        'user_gdpr',
        'user_waiting',
        'user_waiting',
        'encryption_key',
    ]

    def get(self, request, *args, **kwargs):
        if settings.ENABLE_DOMAIN_CHECKER:
            err_txt = "User domain is {} which does not match server domain {}".format(
                request.get_host(), settings.DOMAIN
            )
            assert request.get_host() == settings.DOMAIN, err_txt
        self.admin_validated = cache.get("KEY_DIDS")
        response = super().get(request, *args, **kwargs)

        if not self.admin_validated:
            actual_path = resolve(self.request.path).url_name
            if not self.request.user.is_admin:
                if actual_path != 'user_waiting':
                    return redirect(reverse_lazy("idhub:user_waiting"))

            if self.request.user.is_admin:
                if actual_path != 'encryption_key':
                    return redirect(reverse_lazy("idhub:encryption_key"))

        url = self.check_gdpr()

        return url or response
        
    def post(self, request, *args, **kwargs):
        if settings.ENABLE_DOMAIN_CHECKER:
            err_txt = "User domain is {} which does not match server domain {}".format(
                request.get_host(), settings.DOMAIN
            )
            assert request.get_host() == settings.DOMAIN, err_txt
        self.admin_validated = cache.get("KEY_DIDS")
        response = super().post(request, *args, **kwargs)
        url = self.check_gdpr()

        return url or response

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
            'admin_validated': True if self.admin_validated else False,
            'commit_id': settings.COMMIT, 
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
        
