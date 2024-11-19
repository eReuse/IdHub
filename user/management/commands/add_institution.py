from django.core.management.base import BaseCommand
from user.models import Institution
from lot.models import LotTag

class Command(BaseCommand):
    help = "Create a new Institution"

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='institution')

    def handle(self, *args, **kwargs):
        self.institution = Institution.objects.create(name=kwargs['name'])
        self.create_lot_tags()

    def create_lot_tags(self):
        tags = [
            "Entrada",
            "Salida",
            "Temporal"
        ]
        for tag in tags:
            LotTag.objects.create(
                name=tag,
                owner=self.institution
            )
