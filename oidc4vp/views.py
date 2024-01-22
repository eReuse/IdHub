import json
import base64

from django.conf import settings
from django.views.generic.edit import View, FormView
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from django.contrib import messages

from oidc4vp.models import Authorization, Organization, OAuth2VPToken
from idhub.mixins import UserView
from idhub.models import Event

from oidc4vp.forms import AuthorizeForm
from utils.idhub_ssikit import verify_presentation


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
        except:
            vps = []
        kwargs['presentation_definition'] = vps
        kwargs["org"] = self.get_org()
        kwargs["code"] = self.request.GET.get('code')
        enc_pw = self.request.session["key_did"]
        kwargs['pw'] = self.request.user.decrypt_data(
            enc_pw,
            self.request.user.password+self.request.session._session_key
        )
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
        except:
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

        vp_token = OAuth2VPToken(
            vp_token = vp_tk,
            organization=org,
            code=code
        )
        if not vp_token.authorization:
            raise Http404("Page not Found!")

        vp_token.verifing()
        response = vp_token.get_response_verify()
        vp_token.save()
        if not vp_token.authorization.promotions.exists():
            response["response"] = "Validation Code {}".format(code)

        return JsonResponse(response)

    def validate(self, request):
        auth_header = request.headers.get('Authorization', b'')
        auth_data = auth_header.split()

        if len(auth_data) == 2 and auth_data[0].lower() == 'basic':
            decoded_auth = base64.b64decode(auth_data[1]).decode('utf-8')
            client_id, client_secret = decoded_auth.split(':', 1)
            org_url = request.GET.get('demand_uri')
            org = get_object_or_404(
                    Organization,
                    client_id=client_id,
                    client_secret=client_secret
                )
            return org

        raise Http404("Page not Found!")

        
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
            raise Http404("Page not Found!")

        return redirect(promotion.get_url(code))

