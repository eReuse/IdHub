import logging
import requests

from django.core.management.base import BaseCommand
from django.conf import settings
from dpp.models import MemberFederated


logger = logging.getLogger('django')


class Command(BaseCommand):
    help = "Synchronize members of DLT"

    def handle(self, *args, **kwargs):
        api = settings.API_RESOLVER
        if not api:
            logger.error("you need set the var API_RESOLVER")
            return


        api = api.strip("/")

        url = api + '/getAll'
        res = requests.get(url)
        if res.status_code != 200:
            return "Error, {}".format(res.text)
        response = res.json()
        members = response['url']
        counter = members.pop('counter')
        if counter <= MemberFederated.objects.count():
            logger.info("Synchronize members of DLT -> All Ok")
            return "All ok"

        for k, v in members.items():
            id = self.clean_id(k)
            member = MemberFederated.objects.filter(dlt_id_provider=id).first()
            if member:
                if member.domain != v:
                    member.domain = v
                    member.save()
                continue
            MemberFederated.objects.create(dlt_id_provider=id, domain=v)
        return res.text

    def clean_id(self, id):
        return int(id.split('DH')[-1])
