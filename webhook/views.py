import logging
from uuid import uuid4

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django_tables2 import SingleTableView

from idhub.mixins import AdminView
from webhook.models import Token
from webhook.tables import TokensTable

from .forms import TokenCreateForm, TokenUpdateForm


logger = logging.getLogger(__name__)

#webhook verify and issue moved to and idhub.api.api.py

class WebHookTokenView(AdminView, SingleTableView):
    template_name = "token.html"
    title = _("Credential management")
    section = "Credential"
    subtitle = _('Management Tokens')
    icon = 'bi bi-key'
    model = Token
    table_class = TokensTable

    def get_queryset(self):
        """
        Override the get_queryset method to filter events based on the user type.
        """
        return Token.objects.filter().order_by("-id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'tokens': Token.objects,
        })
        return context


class TokenDeleteView(AdminView, DeleteView):
    model = Token

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        self.object.delete()

        return redirect('webhook:tokens')


class TokenStatusView(AdminView, DeleteView):
    model = Token

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk)
        if self.object.active:
            self.object.active = False
        else:
            self.object.active = True
        self.object.save()

        return redirect('webhook:tokens')


class TokenNewView(AdminView, CreateView):
    title = _("Token management")
    section = "Credential"
    subtitle = _('New Tokens')
    icon = 'bi bi-key'
    title = "Token"
    template_name = "new_token.html"
    model = Token
    form_class = TokenCreateForm
    success_url = reverse_lazy('webhook:tokens')
    # def get(self, request, *args, **kwargs):
    #     self.check_valid_user()
    #     Token.objects.create(token=uuid4())

    #     return redirect('webhook:tokens')

    def form_valid(self, form):
        form.instance.token = uuid4()
        form.instance.owner = self.request.user
        form.save()
        return super().form_valid(form)


class TokenUpdateView(AdminView, UpdateView):
    title = _("Token management")
    section = "Credential"
    subtitle = _('Edit Token')
    icon = 'bi bi-pencil'
    template_name = "new_token.html"
    model = Token
    form_class = TokenUpdateForm
    success_url = reverse_lazy('webhook:tokens')
