from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import views as auth_views
from django.contrib.auth import login as auth_login
from django.http import HttpResponseRedirect, HttpResponse

from idhub.models import DID
from trustchain_idhub import settings


class LoginView(auth_views.LoginView):
    template_name = 'auth/login.html'
    extra_context = {
        'title': _('Login'),
        'success_url': reverse_lazy('idhub:user_dashboard'),
    }

    def get(self, request, *args, **kwargs):
        self.extra_context['success_url'] = request.GET.get(
            'next',
            reverse_lazy('idhub:user_dashboard')
        )
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_anonymous and user.is_admin:
            admin_dashboard = reverse_lazy('idhub:admin_dashboard')
            self.extra_context['success_url'] = admin_dashboard
        auth_login(self.request, user)
        return HttpResponseRedirect(self.extra_context['success_url'])


def serve_did(request, did_id):
    document = get_object_or_404(DID, did=f'did:web:{settings.DOMAIN}:{did_id}').didweb_document
    retval = HttpResponse(document)
    retval.headers["Content-Type"] = "application/json"
    return retval
