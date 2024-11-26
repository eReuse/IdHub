import json
import logging

from ereuseapi.methods import API
from django.conf import settings
from django.core.management.base import BaseCommand
from user.models import User, Institution
from dpp.models import UserDpp


logger = logging.getLogger('django')


class Command(BaseCommand):
    help = "Insert users than are in Dlt with params: path of data set file"

    
    def add_arguments(self, parser):
        parser.add_argument('dataset_file', type=str, help='institution')

    def handle(self, *args, **kwargs):
        dataset_file = kwargs.get("dataset_file")
        self.api_dlt = settings.API_DLT
        self.institution = Institution.objects.filter().first()
        if not self.api_dlt:
            logger.error("you need set the var API_DLT")
            return

        self.api_dlt = self.api_dlt.strip("/")
        
        with open(dataset_file) as f:
            dataset = json.loads(f.read())

        self.add_user(dataset)
        
    def add_user(self, data):
        email = data.get("email")
        password = data.get("password")
        api_token = data.get("api_token")
        # ethereum = {"data": {"api_token": api_token}}
        # data_eth = json.dumps(ethereum)
        data_eth = json.dumps(api_token)
        # TODO encrypt in the future
        # api_keys_dlt = encrypt(password, data_eth)
        api_keys_dlt = data_eth
                
        user = User.objects.filter(email=email).first()

        if not user:
            user = User.objects.create(
                email=email,
                password=password,
                institution = self.institution
            )

        roles = []
        token_dlt = api_token
        api = API(self.api_dlt, token_dlt, "ethereum")
        result = api.check_user_roles()

        if result.get('Status') == 200:
            if 'Success' in result.get('Data', {}).get('status'):
                rols = result.get('Data', {}).get('data', {})
                roles = [(k, k) for k, v in rols.items() if v]

        roles_dlt = json.dumps(roles)

        UserDpp.objects.create(
            roles_dlt=roles_dlt,
            api_keys_dlt=api_keys_dlt,
            user=user
        )
