import json
import uuid
import logging

from uuid import uuid4

from django.urls import reverse_lazy
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django_tables2 import SingleTableView
from django.views.generic.edit import (
    CreateView,
    DeleteView,
    UpdateView,
)

from utils.save_snapshots import move_json, save_in_disk
from django.views.generic.edit import View
from dashboard.mixins import DashboardView
from evidence.models import Annotation
from evidence.parse_details import ParseSnapshot
from evidence.parse import Build
from device.models import Device
from api.models import Token
from api.tables import TokensTable


logger = logging.getLogger('django')


class ApiMixing(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def auth(self):
        # Authentication
        auth_header = self.request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.error("Invalid or missing token %s", auth_header)
            return JsonResponse({'error': 'Invalid or missing token'}, status=401)

        token = auth_header.split(' ')[1].strip("'").strip('"')
        try:
            uuid.UUID(token)
        except Exception:
            logger.error("Invalid or missing token %s", token)
            return JsonResponse({'error': 'Invalid or missing token'}, status=401)

        self.tk = Token.objects.filter(token=token).first()

        if not self.tk:
            logger.error("Invalid or missing token %s", token)
            return JsonResponse({'error': 'Invalid or missing token'}, status=401)


class NewSnapshotView(ApiMixing):

    def get(self, request, *args, **kwargs):
        return JsonResponse({}, status=404)

    def post(self, request, *args, **kwargs):
        response = self.auth()
        if response:
            return response

        # Validation snapshot
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            txt = "error: the snapshot is not a json"
            logger.error("%s", txt)
            return JsonResponse({'error': 'Invalid JSON'}, status=500)

        # Process snapshot
        path_name = save_in_disk(data, self.tk.owner.institution.name)

        # try:
        #     Build(data, None, check=True)
        # except Exception:
        #     return JsonResponse({'error': 'Invalid Snapshot'}, status=400)

        if not data.get("uuid"):
            txt = "error: the snapshot not have uuid"
            logger.error("%s", txt)
            return JsonResponse({'status': txt}, status=500)

        exist_annotation = Annotation.objects.filter(
            uuid=data['uuid']
        ).first()

        if exist_annotation:
            txt = "error: the snapshot {} exist".format(data['uuid'])
            logger.warning("%s", txt)
            return JsonResponse({'status': txt}, status=500)


        try:
            Build(data, self.tk.owner)
        except Exception as err:
            if settings.DEBUG:
                logger.exception("%s", err)
            snapshot_id = data.get("uuid", "")
            txt = "It is not possible to parse snapshot: %s."
            logger.error(txt, snapshot_id)
            text = "fail: It is not possible to parse snapshot"
            return JsonResponse({'status': text}, status=500)

        annotation = Annotation.objects.filter(
            uuid=data['uuid'],
            type=Annotation.Type.SYSTEM,
            # TODO this is hardcoded, it should select the user preferred algorithm
            key="hidalgo1",
            owner=self.tk.owner.institution
        ).first()


        if not annotation:
            logger.error("Error: No annotation for uuid: %s", data["uuid"])
            return JsonResponse({'status': 'fail'}, status=500)

        url_args = reverse_lazy("device:details", args=(annotation.value,))
        url = request.build_absolute_uri(url_args)

        response = {
            "status": "success",
            "dhid": annotation.value[:6].upper(),
            "url": url,
            # TODO replace with public_url when available
            "public_url": url
        }
        move_json(path_name, self.tk.owner.institution.name)

        return JsonResponse(response, status=200)


class TokenView(DashboardView, SingleTableView):
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
            'tokens': Token.objects.all(),
        })
        return context


class TokenDeleteView(DashboardView, DeleteView):
    model = Token

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = get_object_or_404(self.model, pk=self.pk, owner=self.request.user)
        self.object.delete()

        return redirect('api:tokens')


class TokenNewView(DashboardView, CreateView):
    template_name = "new_token.html"
    title = _("Credential management")
    section = "Credential"
    subtitle = _('New Tokens')
    icon = 'bi bi-key'
    model = Token
    success_url = reverse_lazy('api:tokens')
    fields = (
        "tag",
    )

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.token = uuid4()
        return super().form_valid(form)


class EditTokenView(DashboardView, UpdateView):
    template_name = "new_token.html"
    title = _("Credential management")
    section = "Credential"
    subtitle = _('New Tokens')
    icon = 'bi bi-key'
    model = Token
    success_url = reverse_lazy('api:tokens')
    fields = (
        "tag",
    )

    def get_form_kwargs(self):
        pk = self.kwargs.get('pk')
        self.object = get_object_or_404(
            self.model,
            owner=self.request.user,
            pk=pk,
        )
        kwargs = super().get_form_kwargs()
        return kwargs


class DetailsDeviceView(ApiMixing):

    def get(self, request, *args, **kwargs):
        response = self.auth()
        if response:
            return response

        self.pk = kwargs['pk']
        self.object = Device(id=self.pk)

        if not self.object.last_evidence:
            return JsonResponse({}, status=404)

        if self.object.owner != self.tk.owner.institution:
            return JsonResponse({}, status=403)

        data = self.get_data()
        return JsonResponse(data, status=200)

    def post(self, request, *args, **kwargs):
        return JsonResponse({}, status=404)

    def get_data(self):
        data = {}
        self.object.initial()
        self.object.get_last_evidence()
        evidence = self.object.last_evidence

        if evidence.is_legacy():
            data.update({
                "device": evidence.get("device"),
                "components": evidence.get("components"),
            })
        else:
            evidence.get_doc()
            snapshot = ParseSnapshot(evidence.doc).snapshot_json
            data.update({
                "device": snapshot.get("device"),
                "components": snapshot.get("components"),
            })

        uuids = Annotation.objects.filter(
            owner=self.tk.owner.institution,
            value=self.pk
        ).values("uuid")

        annotations = Annotation.objects.filter(
            uuid__in=uuids,
            owner=self.tk.owner.institution,
            type = Annotation.Type.USER
        ).values_list("key", "value")

        data.update({"annotations": list(annotations)})
        return data


class AddAnnotationView(ApiMixing):

    def post(self, request, *args, **kwargs):
        response = self.auth()
        if response:
            return response

        self.pk = kwargs['pk']
        institution = self.tk.owner.institution
        self.annotation = Annotation.objects.filter(
            owner=institution,
            value=self.pk,
            type=Annotation.Type.SYSTEM
        ).first()

        if not self.annotation:
            return JsonResponse({}, status=404)

        try:
            data = json.loads(request.body)
            key = data["key"]
            value = data["value"]
        except Exception:
            logger.error("Invalid Snapshot of user %s", self.tk.owner)
            return JsonResponse({'error': 'Invalid JSON'}, status=500)

        Annotation.objects.create(
            uuid=self.annotation.uuid,
            owner=self.tk.owner.institution,
            type = Annotation.Type.USER,
            key = key,
            value = value
        )

        return JsonResponse({"status": "success"}, status=200)

    def get(self, request, *args, **kwargs):
        return JsonResponse({}, status=404)
