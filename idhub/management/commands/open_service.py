from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.cache import cache


class Command(BaseCommand):
    help = "Command for open de service"

    def add_arguments(self, parser):
        parser.add_argument('key', nargs='?', default='', type=str, help='key')

    def handle(self, *args, **kwargs):
        PASSWORD = kwargs["key"]
        cache.set("KEY_DIDS", PASSWORD, None)
        call_command('runserver')
