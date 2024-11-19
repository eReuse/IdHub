from django.views.generic.edit import View
from django.http import JsonResponse

from evidence.xapian import search
from dpp.models import Proof
from dpp.api_dlt import ALGORITHM


class ProofView(View):
    
    def get(self, request, *args, **kwargs):
        timestamp = kwargs.get("proof_id")
        proof = Proof.objects.filter(timestamp=timestamp).first()
        if not proof:
            return JsonResponse({}, status=404)

        ev_uuid = 'uuid:"{}"'.format(proof.uuid)
        matches = search(None, ev_uuid, limit=1)
        if not matches or matches.size() < 1:
            return JsonResponse({}, status=404)
        
        for x in matches:
            snap = x.document.get_data()
            
            data = {
                "algorithm": ALGORITHM,
                "document": snap
            }

            d = {
                '@context': ['https://ereuse.org/proof0.json'],
                'data': data,
            }
            return JsonResponse(d, status=200)

        return JsonResponse({}, status=404)
