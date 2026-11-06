from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy, resolve
from django.shortcuts import redirect
from django.core.cache import cache
from django.conf import settings
from django.contrib import messages
from oidc4vp.models import Organization


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
        'encryption_key',
    ]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if getattr(settings, 'ENABLE_DOMAIN_CHECKER', False):
            err_txt = "User domain is {} which does not match server domain {}".format(
                request.get_host(), settings.domain
            )
            assert request.get_host() == settings.domain, err_txt

        self.admin_validated = cache.get("KEY_DIDS")

        if not self.admin_validated:
            actual_path = resolve(self.request.path).url_name
            if not self.request.user.is_admin:
                if actual_path != 'user_waiting':
                    return redirect(reverse_lazy("idhub:user_waiting"))

            if self.request.user.is_admin:
                allowed_admin_paths = ['encryption_key', 'admin_2fauth', 'confirm_send_2f']
                if actual_path not in allowed_admin_paths:
                    self.request.session['next_after_enc'] = self.request.get_full_path()
                    return redirect(reverse_lazy("idhub:encryption_key"))

        url = self.check_gdpr()
        if url:
            return url

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        org = Organization.objects.filter(main=True).first()
        context = super().get_context_data(**kwargs)
        context.update({
            'title': getattr(self, 'title', ''),
            'subtitle': getattr(self, 'subtitle', ''),
            'icon': getattr(self, 'icon', ''),
            'section': getattr(self, 'section', ''),
            'path': resolve(self.request.path).url_name,
            'user': self.request.user,
            'wallet': self.wallet,
            'admin_validated': True if self.admin_validated else False,
            'commit_id': settings.COMMIT,
            'org': org,
        })
        return context

    def check_gdpr(self):
        if not self.request.user.accept_gdpr:
            url = reverse_lazy("idhub:user_terms_and_conditions")
            if self.request.user.is_admin:
                url = reverse_lazy("idhub:admin_terms_and_conditions")
            if resolve(self.request.path).url_name not in self.path_terms:
                return redirect(url)
        return None


class AdminView(UserView):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.check_valid_user():
            return redirect(reverse_lazy('idhub:user_dashboard'))

        return super().dispatch(request, *args, **kwargs)

    def check_valid_user(self):
        if not self.request.user.is_admin:
            txt = _("User is not authorized to see admin pages, redirected to user dashboard")
            messages.error(self.request, txt)
            return True

        if self.request.session.get("2fauth"):
            raise Http403()

        return False
