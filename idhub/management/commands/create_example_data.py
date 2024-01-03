import random
from typing import Type, Callable, List

from django.core.management.base import BaseCommand
from django.db import models, IntegrityError

from idhub.models import Event, Rol, Service, UserRol
from idhub_auth.models import User

from faker import Faker

DEFAULT_OBJECTS_CREATED: int = 30
RANDOM_STRING_LENGTH: int = 30
EMAIL_RANDOM_STRING_LENGTH: int = 10
EXISTING_EVENTS: int = 30

fake = Faker()


class Command(BaseCommand):
    """
    Populate the database with dummy values.
    You can either specify which model to create objects for,
    or create objects for all models.
    If no data is specified it will create 30 events, users,
    services, roles, and user roles.
    """

    help = 'Populate the database with dummy values for testing.'

    def __init__(self, *args, **kwargs):
        """
        In the context of a Django management command,
        initializing lists like created_users in the constructor ensures
        that each run of the command has its own set of users, services,
        roles, etc., and does not unintentionally share or retain state
        across different invocations of the command.
        """
        super().__init__(*args, **kwargs)
        self.created_users = []
        self.created_services = []
        self.created_roles = []

    def handle(self, *args, **options):
        any_option_used = self.process_options(options)

        if not any_option_used:
            self.create_all()

    def process_options(self, input_options):
        option_methods = {
            'events': self.create_events,
            'users': self.create_users,
            'superusers': self.create_superusers,
            'services': self.create_services,
            'roles': self.create_roles,
            'userroles': self.create_user_roles,
            'userrole': self.create_specific_user_role,
            'register': self.register_user,
            'register_superuser': self.register_superuser,
            'amount': self.create_all
        }

        any_option_used = self.match_input_to_options(input_options,
                                                      option_methods)

        return any_option_used

    def match_input_to_options(self, input_options, option_methods):
        any_option_used = False

        for option, method in option_methods.items():
            is_valid_option = option in input_options and input_options[
                option] is not None
            if is_valid_option:
                self.call_selected_method(input_options, method, option)
                any_option_used = True

        return any_option_used

    def call_selected_method(self, input_options, method, option):
        args = self.create_argument_list(input_options, option)
        method(*args)

    def create_argument_list(self, input_options, option):
        if isinstance(input_options[option], list):
            args = input_options[option]
        else:
            args = [input_options[option]]
        return args

    def add_arguments(self, parser):
        parser.add_argument(
            '--amount', type=int, action='store',
            help='Create N objects (includes events, users, services, roles, and user roles)'
        )
        parser.add_argument('--events', type=int,
                            help='Create the specified number of events')
        parser.add_argument('--users', type=int,
                            help='Create the specified number of users')
        parser.add_argument('--superusers', type=int,
                            help='Create the specified number of superusers')
        parser.add_argument('--services', type=int,
                            help='Create the specified number of services')
        parser.add_argument('--roles', type=int,
                            help='Create the specified number of roles')
        parser.add_argument('--userroles', type=int,
                            help='Create the specified number of user roles')
        parser.add_argument(
            '--userrole', nargs=2, type=str,
            help='Create a user role for user U and service S',
            metavar=('U', 'S'),
        )
        parser.add_argument('--register', nargs=2, type=str,
                            help='Create a user with email EMAIL and password PW',
                            metavar=('EMAIL', 'PW'))
        parser.add_argument('--register-superuser', nargs=2, type=str,
                            help='Create a superuser with email EMAIL and '
                                 'password PW',
                            metavar=('EMAIL', 'PW'))

    def register_user(self, email: str, password: str):
        """
        Register a new user with the given email and password from the command line.
        """
        try:
            self.create_user(email, password)
            self.stdout.write(f"Successfully registered user: {email}")
        except IntegrityError:
            self.stdout.write(f"Failed to register user: {email}")

    def register_superuser(self, email: str, password: str):
        """
        Register a new superuser with the given email and password from the command line.
        """
        try:
            self.create_superuser(email, password)
            self.stdout.write(f"Successfully registered superuser: {email}")
        except IntegrityError:
            self.stdout.write(f"Failed to register superuser: {email}")

    def create_all(self, amount=DEFAULT_OBJECTS_CREATED):
        self.create_events(amount)
        self.create_users(amount)
        self.create_roles(amount)
        self.create_services(amount)
        self.create_user_roles(amount)

    def create_objects(self, model: Type[models.Model],
                       data_generator: Callable, amount: int) -> List[
        models.Model]:
        """
        Generic method to create objects for a given model and keep track of them.

        Args:
            model: The Django model class for which objects are to be created.
            data_generator: A function that returns a dictionary of attributes for creating a model instance.
            amount: The number of objects to create.

        Returns:
            A list of successfully created model instances.
        """
        created_objects = []
        for _ in range(amount):
            try:
                model_instance = self.create_from_data(data_generator, model)
                created_objects.append(model_instance)
            except IntegrityError:
                self.print_failure_message(model)

        self.print_amount_created(created_objects, model)
        return created_objects

    def create_users(self, amount: int):
        def user_data():
            return {
                'email': fake.email(),
                'first_name': fake.first_name(),
                'last_name': fake.last_name()
            }
        created_users = self.create_objects(User, user_data, amount)
        self.created_users.extend(created_users)

    def create_events(self, amount: int, user=None):
        def event_data():
            return {
                'type': random.randint(1, EXISTING_EVENTS),
                'message': fake.paragraph(nb_sentences=3),
                'user': user
            }
        self.create_objects(Event, event_data, amount)

    def create_superusers(self, amount=0):
        """Superusers can only be created from the specific command"""
        created_superuser_amount = 0
        for value in range(0, amount):
            email = fake.email()
            try:
                User.objects.create_superuser(email)
                created_superuser_amount += 1
            except IntegrityError:
                self.stdout.write("Couldn't create superuser " + email)
        self.stdout.write(f"Created {created_superuser_amount} users")

    def create_services(self, amount: int):
        def service_data():
            domain = fake.text(max_nb_chars=200)
            description = fake.text(max_nb_chars=250)
            return {
                'domain': domain,
                'description': description,
            }

        created_services = self.create_objects(Service, service_data, amount)
        self.associate_random_roles(created_services)
        self.created_services.extend(created_services)

    def create_roles(self, amount: int):
        def role_data():
            name = fake.job()
            description = fake.text(max_nb_chars=250)
            return {'name': name, 'description': description}

        created_roles = self.create_objects(Rol, role_data, amount)
        self.created_roles.extend(created_roles)

    def create_user_roles(self, amount: int, user_id=None, service_id=None):
        def user_role_data():
            user = self.get_or_create_user(user_id)
            service = self.get_or_create_service(service_id)
            return {"user": user, "service": service}

        self.create_objects(UserRol, user_role_data, amount)

    def create_specific_user_role(self, user, service):
        self.create_user_roles(1, user, service)

    def create_user(self, email: str, password: str):
        User.objects.create_user(email, password)

    def create_superuser(self, email: str, password: str):
        User.objects.create_superuser(email, password)

    def print_failure_message(self, model):
        self.stdout.write(f"Couldn't create {model.__name__} object.")

    def print_amount_created(self, created_objects, model):
        self.stdout.write(f"Created {len(created_objects)} "
                          f"{model.__name__} objects")

    def create_from_data(self, data_generator, model):
        model_instance = model.objects.create(**data_generator())
        return model_instance

    def associate_random_roles(self, created_services):
        for service in created_services:
            self.associate_service_to_random_roles(service)

    def associate_service_to_random_roles(self, service):
        associated_roles = [self.get_or_create_role() for _ in range(
            random.randint(0, 2))]
        service.rol.set(associated_roles)

    def get_or_create_user(self, user_id):
        if user_id is not None:
            user = User.objects.get(user_id=user_id)
        elif len(self.created_users) != 0:
            user = random.choice(self.created_users)
        else:
            self.create_users(1)
            user = self.created_users[0]

        return user

    def get_or_create_service(self, service_id):
        if service_id is not None:
            service = Service.objects.get(service_id=service_id)
        elif len(self.created_services) != 0:
            service = random.choice(self.created_services)
        else:
            self.create_services(1)
            service = self.created_services[0]

        return service

    def get_or_create_role(self):
        if len(self.created_roles) != 0:
            role = random.choice(self.created_roles)
        else:
            self.create_roles(1)
            role = self.created_roles[0]

        return role