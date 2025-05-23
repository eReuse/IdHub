from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


User = get_user_model()


class Command(BaseCommand):
    help = "create a admin user"

    def handle(self, *args, **kwargs):
        email = settings.INIT_ADMIN_EMAIL
        password = settings.INIT_ADMIN_PASSWORD
        User.objects.create_superuser(email=email, password=password)
