from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from oidc4vp.models import Organization


User = get_user_model()


class Command(BaseCommand):
    help = "create Organization"
    DOMAIN = settings.DOMAIN

    def add_arguments(self, parser):
        parser.add_argument('name', nargs='?', default='', type=str, help='Name of the organization')

    def handle(self, *args, **kwargs):
        self.name = kwargs['name']

        Organization.objects.create(
            name=self.name,
            domain=self.DOMAIN,
            main=True
        )
