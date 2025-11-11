from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


User = get_user_model()


class Command(BaseCommand):
    help = "Create a admin user"

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='email')
        parser.add_argument('password', type=str, help='password')

    def handle(self, *args, **kwargs):
        email = kwargs['email']
        password = kwargs['password']
        u = User.objects.create_superuser(email=email, password=password)
        u.set_encrypted_sensitive_data()
        u.save()
