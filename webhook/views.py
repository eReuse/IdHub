import json

from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import DeleteView
from django.views.generic.base import View
from django.core.cache import cache
from django.http import JsonResponse
from django_tables2 import SingleTableView
from pyvckit.verify import verify_vp, verify_vc
from uuid import uuid4

from idhub.mixins import AdminView
from idhub_auth.models import User
from idhub.models import DID, Schemas, VerificableCredential
from webhook.models import Token
from webhook.tables import TokensTable


@csrf_exempt
def webhook_verify(request):
    if request.method == 'POST':
        user = User.objects.filter(is_admin=True).first()
        if not cache.get("KEY_DIDS") or not user.accept_gdpr:
            return JsonResponse({'error': 'Temporary out of service'}, status=400)

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Invalid or missing token'}, status=401)

        token = auth_header.split(' ')[1].strip("'").strip('"')
        tk = Token.objects.filter(token=token).first()
        if not tk:
            return JsonResponse({'error': 'Invalid or missing token'}, status=401)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        typ = data.get("type")
        vc = data.get("data")
        try:
            vc = json.dumps(vc)
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        func = verify_vp
        if typ == "credential":
            func = verify_vc

        if func(vc):
            return JsonResponse({'status': 'success'}, status=200)

        return JsonResponse({'status': 'fail'}, status=200)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def webhook_issue(request):
    if request.method == 'POST':
        user = User.objects.filter(is_admin=True).first()
        if not cache.get("KEY_DIDS") or not user.accept_gdpr:
            return JsonResponse({'error': 'Temporary out of service'}, status=400)

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Invalid or missing token'}, status=401)

        token = auth_header.split(' ')[1].strip("'").strip('"')
        tk = Token.objects.filter(token=token).first()
        if not tk:
            return JsonResponse({'error': 'Invalid or missing token'}, status=401)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        typ = data.get("type")
        vc = data.get("data")
        save = data.get("save", True)
        try:
            vc = json.dumps(vc)
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not typ or not vc:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        did = DID.objects.filter(user__isnull=True).first()
        if not did:
            return JsonResponse({'error': 'Invalid DID'}, status=400)

        schema = Schemas.objects.filter(type=typ).first()
        if not schema:
            return JsonResponse({'error': 'Invalid credential'}, status=400)

        cred = VerificableCredential(
            csv_data=vc,
            issuer_did=did,
            schema=schema,
            user=user
        )

        cred.set_type()
        vc_signed = cred.issue(did, domain=request.get_host(), save=save)

        if not vc_signed:
            return JsonResponse({'error': 'Invalid credential'}, status=400)

        return JsonResponse({'status': 'success', "data": vc_signed}, status=200)

        return JsonResponse({'status': 'fail'}, status=200)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


class WebHookTokenView(AdminView, SingleTableView):
    template_name = "token.html"
    title = _("Credential management")
    section = "Credential"
    subtitle = _('Managament Tokens')
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


class TokenNewView(AdminView, View):

    def get(self, request, *args, **kwargs):
        self.check_valid_user()
        Token.objects.create(token=uuid4())

        return redirect('webhook:tokens')
