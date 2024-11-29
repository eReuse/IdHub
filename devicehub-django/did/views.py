import json
import logging

from django.http import JsonResponse, Http404
from django.views.generic.base import TemplateView
from device.models import Device
from evidence.parse import Build
from dpp.api_dlt import ALGORITHM
from dpp.models import Proof
from dpp.api_dlt import PROOF_TYPE


logger = logging.getLogger('django')


class PublicDeviceWebView(TemplateView):
    template_name = "device_did.html"

    def get(self, request, *args, **kwargs):
        self.pk = kwargs['pk']
        chid = self.pk.split(":")[0]
        proof = Proof.objects.filter(signature=self.pk).first()
        if proof:
            self.object = Device(id=chid, uuid=proof.uuid)
        else:
            self.object = Device(id=chid)

        if not self.object.last_evidence:
            raise Http404

        if self.request.headers.get('Accept') == 'application/json':
            return self.get_json_response()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        self.context = super().get_context_data(**kwargs)
        self.object.initial()
        roles = [("Operator", "Operator")]
        role = "Operator"
        if self.request.user.is_anonymous:
            roles = []
            role = None
        self.context.update({
            'object': self.object,
            'role': role,
            'roles': roles,
            'path': self.request.path,
            'last_dpp': "",
            'before_dpp': "",
        })
        if not self.request.user.is_anonymous:
            self.get_manuals()
        return self.context

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
        device_data = self.get_result()
        # device_data = self.get_device_data()
        response = JsonResponse(device_data)
        response["Access-Control-Allow-Origin"] = "*"
        return response

    def get_result(self):
        components = []
        data = {
            'document': {},
            'dpp': self.pk,
            'algorithm': ALGORITHM,
            'components': components,
            'manufacturer DPP': '',
            'device': {},
        }
        result = {
            '@context': ['https://ereuse.org/dpp0.json'],
            'data': data,
        }

        if len(self.pk.split(":")) > 1:
            dev = Build(self.object.last_evidence.doc, None, check=True)
            doc = dev.get_phid()
            data['document'] = json.dumps(doc)
            data['device'] = dev.device
            data['components'] = dev.components

            self.object.get_evidences()
            last_dpp = Proof.objects.filter(
                uuid__in=self.object.uuids, type=PROOF_TYPE['IssueDPP']
            ).order_by("-timestamp").first()

            key = self.pk
            if last_dpp:
                key = last_dpp.signature

            url = "https://{}/did/{}".format(
                self.request.get_host(),
                key
            )
            data['url_last'] = url
            return result

        dpps = []
        self.object.initial()
        for d in self.object.evidences:
            d.get_doc()
            dev = Build(d.doc, None, check=True)
            doc = dev.get_phid()
            ev = json.dumps(doc)
            phid = dev.get_signature(doc)
            dpp = "{}:{}".format(self.pk, phid)
            rr = {
                'dpp': dpp,
                'document': ev,
                'algorithm': ALGORITHM,
                'manufacturer DPP': '',
                'device': dev.device,
                'components': dev.components
            }

            dpps.append(rr)
        return {
            '@context': ['https://ereuse.org/dpp0.json'],
            'data': dpps,
        }

    def get_manuals(self):
        manuals = {
            'ifixit': [],
            'icecat': [],
            'details': {},
            'laer': [],
            'energystar': {},
        }
        try:
            params = {
                "manufacturer": self.object.manufacturer,
                "model": self.object.model,
            }
            self.params = json.dumps(params)
            manuals['ifixit'] = self.request_manuals('ifixit')
            manuals['icecat'] = self.request_manuals('icecat')
            manuals['laer'] = self.request_manuals('laer')
            manuals['energystar'] = self.request_manuals('energystar') or {}
            if manuals['icecat']:
                manuals['details'] = manuals['icecat'][0]
        except Exception as err:
            logger.error("Error: {}".format(err))

        self.context['manuals'] = manuals
        self.parse_energystar()

    def parse_energystar(self):
        if not self.context.get('manuals', {}).get('energystar'):
            return

        # Defined in:
        # https://dev.socrata.com/foundry/data.energystar.gov/j7nq-iepp

        energy_types = [
            'functional_adder_allowances_kwh',
            'tec_allowance_kwh',
            'long_idle_watts',
            'short_idle_watts',
            'off_mode_watts',
            'sleep_mode_watts',
            'tec_of_model_kwh',
            'tec_requirement_kwh',
            'work_off_mode_watts',
            'work_weighted_power_of_model_watts',
        ]
        energy = {}
        for field in energy_types:
            energy[field] = []

        for e in self.context['manuals']['energystar']:
            for field in energy_types:
                for k, v in e.items():
                    if not v:
                        continue
                    if field in k:
                        energy[field].append(v)

        for k, v in energy.items():
            if not v:
                energy[k] = 0
                continue
            tt = sum([float(i) for i in v])
            energy[k] = round(tt / len(v), 2)

        self.context['manuals']['energystar'] = energy

    def request_manuals(self, prefix):
        #TODO reimplement manuals service
        response = {
            "laer": [{"metal": 40, "plastic_post_consumer": 27, "plastic_post_industry": 34}],
            "energystar": [{
                'functional_adder_allowances_kwh': 180,
                "long_idle_watts": 240,
                "short_idle_watts": 120,
                "sleep_mode_watts": 30,
                "off_mode_watts": 3,
                "tec_allowance_kwh": 180,
                "tec_of_model_kwh": 150,
                "tec_requirement_kwh": 220,
                "work_off_mode_watts": 70,
                "work_weighted_power_of_model_watts": 240
            }],
            "ifixit": [
                {
                    "image": "https://guide-images.cdn.ifixit.com/igi/156EpI4YdQeVfVPa.medium",
                    "url": "https://es.ifixit.com/Gu%C3%ADa/HP+ProBook+450+G4+Back+Panel+Replacement/171196?lang=en",
                    "title": "HP ProBook 450 G4 Back Panel Replacement"
                },
                {
                    "image": "https://guide-images.cdn.ifixit.com/igi/usTIqCKpuxVWC3Ix.140x105",
                    "url": "https://es.ifixit.com/Gu%C3%ADa/HP+ProBook+450+G4+Display+Assembly+Replacement/171101?lang=en",
                    "title": "Display Assembly Replacement"
                }
            ],
            "icecat": [
                {
                    "logo": "https://images.icecat.biz/img/brand/thumb/1_cf8603f6de7b4c4d8ac4f5f0ef439a05.jpg",
                    "image": "https://guide-images.cdn.ifixit.com/igi/Q2nYjTIQfG6GaI5B.standard",
                    "pdf": "https://icecat.biz/rest/product-pdf?productId=32951710&lang=en",
                    "title": "HP ProBook 450 G3"
                }
            ]
        }
        return response.get(prefix, {})
