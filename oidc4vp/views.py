import json
import base64
import logging
import requests

from django.template import loader
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.views.generic.edit import View, FormView
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model

from oidc4vp.models import Authorization, Organization, OAuth2VPToken
from idhub.mixins import UserView
from idhub.models import Event

from oidc4vp.forms import AuthorizeForm



User = get_user_model()
logger = logging.getLogger(__name__)


class AuthorizeView(UserView, FormView):
    title = _("My wallet")
    section = "MyWallet"
    template_name = "credentials_presentation.html"
    subtitle = _('Credential presentation')
    icon = 'bi bi-patch-check-fill'
    form_class = AuthorizeForm
    success_url = reverse_lazy('idhub:user_demand_authorization')

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if self.request.session.get('next_url'):
            return redirect(reverse_lazy('idhub:user_credentials_request'))
        return response
            
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        try:
            vps = json.loads(self.request.GET.get('presentation_definition'))
        except Exception:
            vps = []
        kwargs['presentation_definition'] = vps
        kwargs["org"] = self.get_org()
        kwargs["code"] = self.request.GET.get('code')
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        if form.all_credentials.exists() and not form.credentials.exists():
            self.request.session['next_url'] = self.request.get_full_path()
        return form
    
    def form_valid(self, form):
        authorization = form.save()
        if not authorization or authorization.status_code != 200:
            messages.error(self.request, _("Error sending credential!"))
            return redirect(self.success_url)
        try:
            authorization = authorization.json()
        except Exception:
            messages.error(self.request, _("Error sending credential!"))
            return redirect(self.success_url)

        verify = authorization.get('verify')
        result, msg = verify.split(",")
        if 'error' in result.lower():
            messages.error(self.request, msg)
        if 'ok' in result.lower():
            messages.success(self.request, msg)

        cred = form.credentials.first()
        verifier = form.org.name
        if cred and verifier:
            Event.set_EV_CREDENTIAL_PRESENTED(cred, verifier)

        if authorization.get('redirect_uri'):
            return redirect(authorization.get('redirect_uri'))
        elif authorization.get('response'):
            txt = authorization.get('response')
            messages.success(self.request, txt)
            Event.set_EV_USR_SEND_CREDENTIAL(txt)
            txt2 = f"Verifier {verifier} send: " + txt
            Event.set_EV_USR_SEND_VP(txt2, self.request.user)
            url = reverse_lazy('idhub:user_dashboard')
            return redirect(url)
                
        return redirect(self.success_url)

    def get_org(self):
        client_id = self.request.GET.get("client_id")
        if not client_id:
            raise Http404("Organization not found!")

        org = get_object_or_404(
            Organization,
            client_id=client_id,
        )
        return org
 

@method_decorator(csrf_exempt, name='dispatch')
class VerifyView(View):
    subject_template_name = 'email/verify_subject.txt'
    email_template_name = 'email/verify_email.txt'
    html_email_template_name = 'email/verify_email.html'

    def get(self, request, *args, **kwargs):
        org = self.validate(request)
        presentation_definition = json.dumps(settings.SUPPORTED_CREDENTIALS)
        authorization = Authorization(
            organization=org,
            presentation_definition=presentation_definition
        )
        authorization.save()
        res = json.dumps({"redirect_uri": authorization.authorize()})
        return HttpResponse(res)

    def post(self, request, *args, **kwargs):
        code = self.request.POST.get("code")
        vp_tk = self.request.POST.get("vp_token")

        if not vp_tk or not code:
            raise Http404("Page not Found!")

        org = self.validate(request)

        self.vp_token = OAuth2VPToken(
            vp_token = vp_tk,
            organization=org,
            code=code
        )

        if not self.vp_token.authorization:
            raise Http404("Page not Found!")

        self.vp_token.verifing()
        response = self.vp_token.get_response_verify()
        self.vp_token.save()

        for user in User.objects.filter(is_admin=True):
            self.send_email(user)
        self.send_api()

        response["response"] = "Validation Code {}".format(code)
        return JsonResponse(response)

    def send_api(self):
        data = {"vp": self.vp_token.vp_token, "code": self.vp_token.code}
        url = self.vp_token.org.response_uri
        requests.post(url, data=data)

    def validate(self, request):
        auth_header = request.headers.get('Authorization', b'')
        auth_data = auth_header.split()

        if len(auth_data) == 2 and auth_data[0].lower() == 'basic':
            decoded_auth = base64.b64decode(auth_data[1]).decode('utf-8')
            client_id, client_secret = decoded_auth.split(':', 1)
            org = get_object_or_404(
                    Organization,
                    client_id=client_id,
                    client_secret=client_secret
                )
            return org

        raise Http404("Page not Found!")

    def send_email(self, user):
        """
        Send a email when a user is activated.
        """
        verification = self.vp_token.get_result_verify()
        if not verification:
            return

        if verification.get('errors') or verification.get('warnings'):
            return

        email = self.get_email(user)
        try:
            if settings.ENABLE_EMAIL:
                email.send()
                return

            logger.warning(user.email)
            logger.warning(email.body)

        except Exception as err:
            logger.error(err)
            return

    def get_context(self):
        url_domain = "https://{}/".format(settings.DOMAIN)
        context = {
            "domain": settings.DOMAIN,
            "url_domain": url_domain,
            "verification": self.get_verification(),
            "code": self.vp_token.code,
        }
        return context

    def get_email(self, user):
        context = self.get_context()
        subject = loader.render_to_string(self.subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        body = loader.render_to_string(self.email_template_name, context)
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        email_message = EmailMultiAlternatives(
            subject, body, from_email, [to_email])
        html_email = loader.render_to_string(self.html_email_template_name, context)
        email_message.attach_alternative(html_email, 'text/html')
        return email_message

    def get_verification(self):
        return self.vp_token.get_user_info_all()
        
class AllowCodeView(View):
    def get(self, request, *args, **kwargs):
        code = self.request.GET.get("code")

        if not code:
            raise Http404("Page not Found!")
        self.authorization = get_object_or_404(
                Authorization,
                code=code,
                code_used=False
        )

        promotion = self.authorization.promotions.first()
        if not promotion:
            return redirect(reverse_lazy('oidc4vp:received_code'))

        return redirect(promotion.get_url(code))


class ReceivedCodeView(View):
    template_name = "received_code.html"

    def get(self, request, *args, **kwargs):
        self.context = {}
        template = loader.get_template(
            self.template_name,
        ).render()
        return HttpResponse(template)
