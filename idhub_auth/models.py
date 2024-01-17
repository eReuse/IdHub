import nacl
import base64

from nacl import pwhash
from django.db import models
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser


class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(
            email,
            password=password,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    email = models.EmailField(
        _('Email address'),
        max_length=255,
        unique=True,
    )
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    first_name = models.CharField(_("First name"), max_length=255, blank=True, null=True)
    last_name = models.CharField(_("Last name"), max_length=255, blank=True, null=True)
    encrypted_sensitive_data = models.CharField(max_length=255)
    salt = models.CharField(max_length=255)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin

    @property
    def username(self):
        "Is the email of the user"
        return self.email

    def get_memberships(self):
        members = set(
            str(dict(x.Types.choices)[x.type]) for x in self.memberships.all()
        )
        return ", ".join(members)

    def get_roles(self):
        roles = []
        for s in self.roles.all():
            for r in s.service.rol.all():
                roles.append(r.name)
        return ", ".join(set(roles))

    def derive_key_from_password(self, password):
        kdf = pwhash.argon2i.kdf
        ops = pwhash.argon2i.OPSLIMIT_INTERACTIVE
        mem = pwhash.argon2i.MEMLIMIT_INTERACTIVE
        return kdf(
            nacl.secret.SecretBox.KEY_SIZE,
            password,
            self.get_salt(),
            opslimit=ops,
            memlimit=mem
        )

    def decrypt_sensitive_data(self, password, data=None):
        sb_key = self.derive_key_from_password(password.encode('utf-8'))
        sb = nacl.secret.SecretBox(sb_key)
        if not data:
            data = self.get_encrypted_sensitive_data()
        if not isinstance(data, bytes):
            data = data.encode('utf-8')

        return sb.decrypt(data).decode('utf-8')

    def encrypt_sensitive_data(self, password, data):
        sb_key = self.derive_key_from_password(password.encode('utf-8'))
        sb = nacl.secret.SecretBox(sb_key)
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        
        return base64.b64encode(sb.encrypt(data)).decode('utf-8')

    def get_salt(self):
        return base64.b64decode(self.salt.encode('utf-8'))

    def set_salt(self):
        self.salt = base64.b64encode(nacl.utils.random(16)).decode('utf-8')

    def get_encrypted_sensitive_data(self):
        return base64.b64decode(self.encrypted_sensitive_data.encode('utf-8'))

    def set_encrypted_sensitive_data(self, password):
        key = base64.b64encode(nacl.utils.random(64))
        self.set_salt()

        key_crypted = self.encrypt_sensitive_data(password, key)
        self.encrypted_sensitive_data = key_crypted

    def encrypt_data(self, data, password):
        sb = self.get_secret_box(password)
        value_enc = sb.encrypt(data.encode('utf-8'))
        return base64.b64encode(value_enc).decode('utf-8')

    def decrypt_data(self, data, password):
        # import pdb; pdb.set_trace()
        sb = self.get_secret_box(password)
        value = base64.b64decode(data.encode('utf-8'))
        return sb.decrypt(value).decode('utf-8')

    def get_secret_box(self, password):
        pw = base64.b64decode(password.encode('utf-8')*4)
        sb_key = self.derive_key_from_password(pw)
        return nacl.secret.SecretBox(sb_key)
