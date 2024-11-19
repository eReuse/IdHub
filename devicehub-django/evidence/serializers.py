from rest_framework import serializers
from evidence.models import EvidenceJson

import json

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from evidence.parse import Parse

class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceJson
        fields = ['id', 'title', 'content']

@csrf_exempt
def webhook_verify(request):
    if request.method == 'POST':
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Invalid authorization'}, status=401)

        token = auth_header.split(' ')[1]
        tk = Token.objects.filter(token=token).first()
        if not tk:
            return JsonResponse({'error': 'Invalid authorization'}, status=401)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        try:
            device = Parse(data)
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not device:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        return JsonResponse({"result": "Ok"}, status=200)


    return JsonResponse({'error': 'Invalid request method'}, status=400)
