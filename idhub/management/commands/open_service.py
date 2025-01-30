import logging

from nacl.exceptions import CryptoError
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.cache import cache

from idhub.models import DID


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Command for open de service"

    def add_arguments(self, parser):
        parser.add_argument('key', nargs='?', default='', type=str, help='key')

    def handle(self, *args, **kwargs):
        self._key = kwargs["key"]
        cache.set("KEY_DIDS", self._key, None)

        if not DID.objects.exists():
            cache.set("KEY_DIDS", self._key, None)
            call_command('runserver')
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
        call_command('runserver')
