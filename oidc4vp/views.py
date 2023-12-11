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
        return kwargs
    
    def form_valid(self, form):
        # import pdb; pdb.set_trace()
        authorization = form.save()
        if not authorization or authorization.status_code != 200:
            messages.error(self.request, _("Error sending credential!"))
            return super().form_valid(form)
        try:
            authorization = authorization.json()
        except:
            messages.error(self.request, _("Error sending credential!"))
            return super().form_valid(form)

        verify = authorization.get('verify')
        result, msg = verify.split(",")
        if 'error' in result.lower():
            messages.error(self.request, msg)
        if 'ok' in result.lower():
            messages.success(self.request, msg)

        if authorization.get('redirect_uri'):
            return redirect(authorization.get('redirect_uri'))
        elif authorization.get('response'):
            txt = authorization.get('response')
            messages.success(self.request, txt)
                
        return super().form_valid(form)

    def get_org(self):
        # import pdb; pdb.set_trace()
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
        # import pdb; pdb.set_trace()
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

        vp_token.verifing()
        response = vp_token.get_response_verify()
        vp_token.save()
        if response["redirect_uri"]:
            response["response"] = "Validation Code 255255255"

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
        if not self.authorization.promotions:
            raise Http404("Page not Found!")

        promotion = self.authorization.promotions[0]
        return redirect(promotion.get_url(code))

