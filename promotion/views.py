from django.views.generic.edit import View, FormView
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.http import HttpResponse

from promotion.forms import WalletForm


class PromotionView(View):
    template_name = "somconnexio.tarifes-mobil.html"
    def get(self, request, *args, **kwargs):
        self.context = {}
        template = get_template(
            self.template_name,
        ).render()
        return HttpResponse(template)


class SelectWalletView(FormView):
    template_name = "select_wallet.html"
    form_class = WalletForm
    success_url = reverse_lazy('promotion:select_wallet')
    def get(self, request, *args, **kwargs):
        self.context = {}
        template = get_template(
            self.template_name,
            # context
        ).render()
        return HttpResponse(template)

