import logging
import requests

from django.core.management.base import BaseCommand
from django.conf import settings
from user.models import Institution


logger = logging.getLogger('django')


class Command(BaseCommand):
    help = "Insert a new Institution in DLT"

    def add_arguments(self, parser):
        parser.add_argument('domain', type=str, help='institution')

    def handle(self, *args, **kwargs):
        domain = kwargs.get("domain")
        api = settings.API_RESOLVER
        if not api:
            logger.error("you need set the var API_RESOLVER")
            return
        
        if "http" not in domain:
            logger.error("you need put https:// in %s", domain)
            return
        
        api = api.strip("/")
        domain = domain.strip("/")

        data = {"url": domain}
        url = api + '/registerURL'
        res = requests.post(url, json=data)
        print(res.json())
