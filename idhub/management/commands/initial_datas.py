import os
import csv

from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from decouple import config
from oidc4vp.models import Organization
from promotion.models import Promotion


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
        self.sync_credentials_organizations()

    def create_admin_users(self, email, password):
        User.objects.create_superuser(email=email, password=password)


    def create_users(self, email, password):
        u= User.objects.create(email=email, password=password)
        u.set_password(password)
        u.save()


    def create_organizations(self, name, url):
        Organization.objects.create(name=name, response_uri=url)

    def sync_credentials_organizations(self):
        org1 = Organization.objects.get(name="test1")
        org2 = Organization.objects.get(name="test2")
        org2.my_client_id = org1.client_id
        org2.my_client_secret = org1.client_secret
        org1.my_client_id = org2.client_id
        org1.my_client_secret = org2.client_secret
        org1.save()
        org2.save()
