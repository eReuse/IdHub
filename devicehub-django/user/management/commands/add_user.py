from uuid import uuid4

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from user.models import Institution
from api.models import  Token


User = get_user_model()


class Command(BaseCommand):
    help = "Create a new user"

    def add_arguments(self, parser):
        parser.add_argument('institution', type=str, help='institution')
        parser.add_argument('email', type=str, help='email')
        parser.add_argument('password', type=str, help='password')
        parser.add_argument('is_admin', nargs='?', default=False, type=str, help='is admin')
        parser.add_argument('predefined_token', nargs='?', default='', type=str, help='predefined token')

    def handle(self, *args, **kwargs):
        email = kwargs['email']
        password = kwargs['password']
        is_admin = kwargs['is_admin']
        predefined_token = kwargs['predefined_token']
        institution = Institution.objects.get(name=kwargs['institution'])
        self.create_user(institution, email, password, is_admin, predefined_token)

    def create_user(self, institution, email, password, is_admin, predefined_token):
        self.u = User.objects.create(
            institution=institution,
            email=email,
            password=password,
            is_admin=is_admin,
        )
        self.u.set_password(password)
        self.u.save()
        if predefined_token:
            token = predefined_token
        else:
            token = uuid4()

        Token.objects.create(token=token, owner=self.u)
        print(f"TOKEN: {token}")
