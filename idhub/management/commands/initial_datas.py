import os
import csv

from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from decouple import config
from idhub.models import Organization


User = get_user_model()


class Command(BaseCommand):
    help = "Insert minimum datas for the project"

    def handle(self, *args, **kwargs):
        ADMIN_EMAIL = config('ADMIN_EMAIL', 'admin@example.org')
        ADMIN_PASSWORD = config('ADMIN_PASSWORD', '1234')
        USER_EMAIL = config('USER_EMAIL', 'user1@example.org')
        USER_PASSWORD = config('USER_PASSWORD', '1234')

        self.create_admin_users(ADMIN_EMAIL, ADMIN_PASSWORD)
        self.create_users(USER_EMAIL, USER_PASSWORD)

        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        ORGANIZATION = os.path.join(BASE_DIR, 'examples/organizations.csv')
        with open(ORGANIZATION, newline='\n') as csvfile:
            f = csv.reader(csvfile, delimiter=';', quotechar='"')
            for r in f:
                self.create_organizations(r[0].strip(), r[1].strip())

    def create_admin_users(self, email, password):
        User.objects.create_superuser(email=email, password=password)


    def create_users(self, email, password):
        u= User.objects.create(email=email, password=password)
        u.set_password(password)
        u.save()


    def create_organizations(self, name, url):
        Organization.objects.create(name=name, url=url)
