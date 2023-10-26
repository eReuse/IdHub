import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trustchain_idhub.settings')  # noqa
django.setup()  # noqa

from django.contrib.auth import get_user_model


User = get_user_model()


def create_admin_users(email, password):
    User.objects.create_superuser(email=email, password=password)


def create_users(email, password):
    User.objects.create(email=email, password=password)


def main():
    admin = 'admin@example.org'
    pw_admin = '1234'

    user = 'user1@example.org'
    pw_user = '1234'

    create_admin_users(admin, pw_admin)
    create_users(user, pw_user)


if __name__ == '__main__':
    main()
