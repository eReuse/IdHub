import json

from django.views.generic.edit import View, FormView
from django.shortcuts import redirect
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.http import HttpResponse

from promotion.forms import WalletForm, ContractForm


class PromotionView(View):
    template_name = "somconnexio.tarifes-mobil.html"
    def get(self, request, *args, **kwargs):
        self.context = {}
        template = get_template(
            self.template_name,
        ).render()
        return HttpResponse(template)


class PromotionMobile1View(FormView):
    template_name = "somconnexio_contract.html"
    promotion = None
    vp_tokens = None
    authorization = None
    form_class = ContractForm
    def get(self, request, *args, **kwargs):
        code = self.request.GET.get("code")
        self.get_discount(code)
        self.context = {
            "promotion": self.promotion,
            "verificable_presentation": self.vp_token
        }
        template = get_template(
            self.template_name,
        ).render()
        return HttpResponse(template)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.vp_token.get_user_info()
        kwargs['verificable_presentation'] = self.vp_token
        kwargs["nif"] = self.vp_token.user_info.get("nif", '')
        kwargs["name"] = self.vp_token.user_info.get("name", '')
        kwargs["first_last_name"] = self.vp_token.user_info.get("first_last_name", '')
        kwargs["second_last_name"] = self.vp_token.user_info.get("second_last_name", '')
        kwargs["email"] = self.vp_token.user_info.get("email", '')
        kwargs["email_repeat"] = self.vp_token.user_info.get("email", '')
        kwargs["telephone"] = self.vp_token.user_info.get("telephone", '')
        kwargs["birthday"] = self.vp_token.user_info.get("birthday", '')
        kwargs["gen"] = self.vp_token.user_info.get("gen", '')
        kwargs["lang"] = self.vp_token.user_info.get("lang", '')
        return kwargs

    def form_valid(self, form):
        url = form.save()
        return redirect(url)

    def get_discount(self, code):
        self.authorization = Authorization.objects.filter(
            code=code,
            code_unused=False
        ).first()
        if self.authorization:
            if self.authorization.promotions:
                self.promotion = self.authorization.promotionsp[-1]
            if self.authorization.vp_tokens:
                self.vp_tokens = self.authorization.vp_tokens[-1]
        

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
        kwargs['presentation_definition'] = json.dumps(["MemberShipCard"])
        return kwargs

    def form_valid(self, form):
        url = form.save()
        return redirect(url)

