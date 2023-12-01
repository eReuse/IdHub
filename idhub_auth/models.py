from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from nacl import secret, pwhash


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
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    # TODO: Hay que generar una clave aleatoria para cada usuario cuando se le da de alta en el sistema.
    encrypted_sensitive_data_encryption_key = models.BinaryField(max_length=255)
    # TODO: Hay que generar un salt aleatorio para cada usuario cuando se le da de alta en el sistema.
    salt_of_sensitive_data_encryption_key = models.BinaryField(max_length=255)

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
        kdf = pwhash.argon2i.kdf  # TODO: Move the KDF choice to SETTINGS.PY
        ops = pwhash.argon2i.OPSLIMIT_INTERACTIVE  # TODO: Move the KDF choice to SETTINGS.PY
        mem = pwhash.argon2i.MEMLIMIT_INTERACTIVE  # TODO: Move the KDF choice to SETTINGS.PY
        salt = self.salt_of_sensitive_data_encryption_key
        return kdf(secret.SecretBox.KEY_SIZE, password, salt, opslimit=ops, memlimit=mem)

    def decrypt_sensitive_data_encryption_key(self, password):
        sb_key = self.derive_key_from_password(password)
        sb = secret.SecretBox(sb_key)
        return sb.decrypt(self.encrypted_sensitive_data_encryption_key)

