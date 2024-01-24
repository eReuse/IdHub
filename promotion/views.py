import json

from django.conf import settings
from django.views.generic.edit import View, FormView
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.http import HttpResponse

from oidc4vp.models import Authorization
from promotion.forms import WalletForm, ContractForm


class PromotionView(View):
    template_name = "somconnexio_tarifes_mobil.html"
    def get(self, request, *args, **kwargs):
        self.context = {}
        template = get_template(
            self.template_name,
        ).render()
        return HttpResponse(template)

class ThanksView(View):
    template_name = "somconnexio_thanks.html"
    def get(self, request, *args, **kwargs):
        self.context = {}
        template = get_template(
            self.template_name,
        ).render()
        return HttpResponse(template)


class ContractView(FormView):
    template_name = "somconnexio_contract.html"
    promotion = None
    vp_token = None
    authorization = None
    form_class = ContractForm
    success_url = reverse_lazy('promotion:thanks')

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        code = self.request.GET.get("code")
        self.get_discount(code)
        self.context.update({
            "promotion": self.promotion,
            "verificable_presentation": self.vp_token,
            "sim": 10.0,
            "mensual": 15.0,
            "total": 25.0
        })
        if self.promotion:
            self.context['sim'] = self.promotion.get_discount(self.context["sim"])
            self.context['mensual'] = self.promotion.get_discount(self.context["mensual"])
            self.context['total'] = self.promotion.get_discount(self.context["total"])

        if self.vp_token:
            self.context['verificable_presentation'] = self.vp_token

        return self.context
        
        
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        code = self.request.GET.get("code")
        self.get_discount(code)
        if not self.vp_token:
            return kwargs

        self.vp_token.get_user_info()
        kwargs['initial']["nif"] = self.vp_token.user_info.get("nif", '')
        kwargs['initial']["name"] = self.vp_token.user_info.get("name", '')
        kwargs['initial']["first_last_name"] = self.vp_token.user_info.get("first_last_name", '')
        kwargs['initial']["second_last_name"] = self.vp_token.user_info.get("second_last_name", '')
        kwargs['initial']["email"] = self.vp_token.user_info.get("email", '')
        kwargs['initial']["email_repeat"] = self.vp_token.user_info.get("email", '')
        kwargs['initial']["telephone"] = self.vp_token.user_info.get("telephone", '')
        kwargs['initial']["birthday"] = self.vp_token.user_info.get("birthday", '')
        kwargs['initial']["gen"] = self.vp_token.user_info.get("gen", '')
        kwargs['initial']["lang"] = self.vp_token.user_info.get("lang", '')
        return kwargs

    def form_valid(self, form):
        return super().form_valid(form)

    def get_discount(self, code):
        if not code:
            return
        if self.authorization:
            return

        self.authorization = Authorization.objects.filter(
            code=code,
            code_used=False
        ).first()
        if self.authorization:
            if self.authorization.promotions.exists():
                self.promotion = self.authorization.promotions.all()[0]
            if self.authorization.vp_tokens.exists():
                self.vp_token = self.authorization.vp_tokens.all()[0]
        

class SelectWalletView(FormView):
    template_name = "select_wallet.html"
    form_class = WalletForm
    success_url = reverse_lazy('promotion:select_wallet')
    # def get(self, request, *args, **kwargs):
    #     self.context = {'form': fo}
    #     template = get_template(
    #         self.template_name,
    #         # context
    #     ).render()
    #     return HttpResponse(template)

    # def post(self, request, *args, **kwargs):
    #     super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['presentation_definition'] = json.dumps(settings.SUPPORTED_CREDENTIALS)
        return kwargs

    def form_valid(self, form):
        url = form.save()
        return redirect(url)

