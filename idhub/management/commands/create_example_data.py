import random
import string

from django.core.management.base import BaseCommand
from django.db import IntegrityError
from idhub.models import Event, Rol, Service, UserRol
from idhub_auth.models import User

DEFAULT_OBJECTS_CREATED = 30
RANDOM_STRING_LENGTH = 30
EMAIL_RANDOM_STRING_LENGTH = 10


class Command(BaseCommand):
    """
    Populate the database with dummy values.
    You can either specify which model to create objects for,
    or create objects for all models.
    If no data is specified it will create 30 events, users,
    services, roles, and user roles.
    """

    help = 'Populate the database with dummy values for testing.'
    created_users = []
    created_roles = []
    created_services = []

    def handle(self, *args, **options):
        any_option_used = False

        if options["events"]:
            self.create_events(options["events"])
            any_option_used = True
        if options["users"]:
            self.create_users(options["users"])
            any_option_used = True
        if options["superusers"]:
            self.create_superusers(options["superusers"])
            any_option_used = True
        if options["services"]:
            self.create_services(options["services"])
            any_option_used = True
        if options["roles"]:
            self.create_roles(options["roles"])
            any_option_used = True
        if options["userroles"]:
            self.create_user_roles(options["userroles"])
            any_option_used = True
        if options["userrole"]:
            user = options["userrole"][0]
            service = options["userrole"][1]
            self.create_user_roles(1, user, service)
            any_option_used = True
        if options["register"]:
            email = options["register"][0]
            password = options["register"][1]
            self.create_user(email, password)
        if options["register_superuser"]:
            email = options["register_superuser"][0]
            password = options["register_superuser"][1]
            self.create_superuser(email, password)

        if options["amount"]:
            self.create_all(options["amount"])
            any_option_used = True

        if not any_option_used:
            self.create_all()

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
                            help='Create a user with email E and password P',
                            metavar=('E', 'P'))
        parser.add_argument('--register-superuser', nargs=2, type=str,
                            help='Create a superuser with email E and password P',
                            metavar=('E', 'P'))

    def create_all(self, amount=DEFAULT_OBJECTS_CREATED):
        self.create_events(amount)
        self.create_users(amount)
        self.create_roles(amount)
        self.create_services(amount)
        self.create_user_roles(amount)

    def create_events(self, amount, user=None):
        created_event_amount = 0
        for value in range(0, amount):
            try:
                Event.objects.create(
                        type=random.randint(1, 30),
                        message=create_random_string(),
                        user=user
                )
                created_event_amount += 1
            except IntegrityError:
                self.stdout.write("Couldn't create event")
        self.stdout.write(f"Created {created_event_amount} events")

    def create_users(self, amount):
        created_user_amount = 0
        for value in range(0, amount):
            email = create_random_string(EMAIL_RANDOM_STRING_LENGTH) + "@example.org"
            try:
                User.objects.create(
                        email=email,
                        # Could be improved, maybe using Faker
                        first_name=create_random_string(random.randint(5, 10)),
                        last_name=create_random_string(random.randint(5, 10))
                )
                self.created_users.append(email)
                created_user_amount += 1
            except IntegrityError:
                self.stdout.write("Couldn't create user " + email)

        self.stdout.write(f"Created {created_user_amount} users")

    def create_superusers(self, amount=0):
        """Superusers can only be created from the specific command"""
        created_superuser_amount = 0
        for value in range(0, amount):
            email = create_random_string(EMAIL_RANDOM_STRING_LENGTH)
            try:
                User.objects.create_superuser(email)
                created_superuser_amount += 1
            except IntegrityError:
                self.stdout.write("Couldn't create superuser " + email)
        self.stdout.write(f"Created {created_superuser_amount} users")

    def create_services(self, amount):
        created_service_amount = 0
        for value in range(0, amount):
            domain = create_random_string(random.randint(5, 15))
            try:
                service = Service.objects.create(
                        domain=domain,
                        description=create_random_string(
                            random.randint(50, 100))
                )
                self.created_services.append(domain)
                try:
                    associated_rol = Rol.objects.get(name=random.choice(
                        self.created_roles))
                    service.rol.add(associated_rol.id)
                except IntegrityError:
                    self.stdout.write(
                            f"Couldn't associate role with service {domain}")
                created_service_amount += 1
            except IntegrityError:
                self.stdout.write("Couldn't create service " + domain)
        self.stdout.write(f"Created {created_service_amount} services")

    def create_roles(self, amount):
        created_role_amount = 0
        for value in range(0, amount):
            # Could be improved, maybe using Faker
            name = create_random_string(random.randint(5, 10))
            try:
                Rol.objects.create(name=name,
                                   description=create_random_string(
                                       random.randint(50, 100)))
                created_role_amount += 1
            except IntegrityError:
                self.stdout.write("Couldn't create role " + name)
            self.created_roles.append(name)
        self.stdout.write(f"Created {created_role_amount} roles")

    def create_user_roles(self, amount, user_id=None, service_id=None):
        created_user_role_amount = 0
        user_id = user_id if user_id is not None else random.choice(
                self.created_users)
        service_id = service_id if service_id is not None else random.choice(
                self.created_services)
        for value in range(0, amount):
            try:
                user = User.objects.get(email=user_id)
                service = Service.objects.get(domain=service_id)
                UserRol.objects.create(
                        user=user,
                        service=service
                )
                created_user_role_amount += 1
            except IntegrityError:
                self.stdout.write("Couldn't create user role for user " + user.email)
            user_id = random.choice(self.created_users)
            service_id = random.choice(self.created_services)
        self.stdout.write(f"Created {created_user_role_amount} user roles")

    def create_user(self, email, password):
        User.objects.create_user(email, password)

    def create_superuser(self, email, password):
        User.objects.create_superuser(email, password)


def create_random_string(string_length=RANDOM_STRING_LENGTH):
    return ''.join(random.choices(string.ascii_uppercase + string.digits,
                                  k=string_length))
