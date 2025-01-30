import logging

from nacl.exceptions import CryptoError
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.cache import cache

from idhub.models import DID
from idhub_auth.models import User


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Command for open de service"

    def add_arguments(self, parser):
        parser.add_argument('key', nargs='?', default='', type=str, help='key')
        parser.add_argument('ip_port', nargs='?', default='', type=str, help='ip_port')

    def handle(self, *args, **kwargs):
        self._key = kwargs["key"]
        self.ip_port = kwargs["ip_port"]
        cache.set("KEY_DIDS", self._key, None)

        admin = User.objects.filter(is_admin=True).first()
        admin.accept_gdpr = True
        admin.save()

        if not DID.objects.exists():
            cache.set("KEY_DIDS", self._key, None)
            call_command('runserver', self.ip_port)
            return

        did = DID.objects.first()
        cache.set("KEY_DIDS", self._key, None)

        try:
            did.get_key_material()
        except CryptoError:
            cache.set("KEY_DIDS", None)
            txt = "Key no valid!"
            logger.error(txt)
            return

        cache.set("KEY_DIDS", self._key, None)
        call_command('runserver', self.ip_port)
