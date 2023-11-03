from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from idhub.models import Organization


User = get_user_model()


class Command(BaseCommand):
    help = "Insert minimum datas for the project"

    def handle(self, *args, **kwargs):
        admin = 'admin@example.org'
        pw_admin = '1234'

        user = 'user1@example.org'
        pw_user = '1234'
        organization = [
            ("ExO", "https://verify.exo.cat"),
            ("Somos Connexión", "https://verify.somosconexion.coop")
        ]

        # self.create_admin_users(admin, pw_admin)
        self.create_users(user, pw_user)
        for o in organization:
            self.create_organizations(*o)

    def create_admin_users(self, email, password):
        User.objects.create_superuser(email=email, password=password)


    def create_users(self, email, password):
        u= User.objects.create(email=email, password=password)
        u.set_password(password)
        u.save()


    def create_organizations(self, name, url):
        Organization.objects.create(name=name, url=url)
