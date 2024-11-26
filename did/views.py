from django.http import JsonResponse, Http404
from django.views.generic.base import TemplateView
from device.models import Device


class PublicDeviceWebView(TemplateView):
    template_name = "device_web.html"

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        self.object = Device(id=self.pk)

        if not self.object.last_evidence:
            raise Http404

        if self.request.headers.get('Accept') == 'application/json':
            return self.get_json_response()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object.initial()
        context.update({
            'object': self.object
        })
        return context

    @property
    def public_fields(self):
        return {
            'id': self.object.id,
            'shortid': self.object.shortid,
            'uuids': self.object.uuids,
            'hids': self.object.hids,
            'components': self.remove_serial_number_from(self.object.components),
        }

    @property
    def authenticated_fields(self):
        return {
            'serial_number': self.object.serial_number,
            'components': self.object.components,
        }

    def remove_serial_number_from(self, components):
        for component in components:
            if 'serial_number' in component:
                del component['SerialNumber']
        return components

    def get_device_data(self):
        data = self.public_fields
        if self.request.user.is_authenticated:
            data.update(self.authenticated_fields)
        return data

    def get_json_response(self):
        device_data = self.get_device_data()
        return JsonResponse(device_data)

