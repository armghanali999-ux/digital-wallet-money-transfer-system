from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from accounts.themes import DEFAULT_THEME, THEME_CHOICES


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(role="ADMIN", is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        ADMIN = "ADMIN", "Administrator"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"

    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CUSTOMER)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    theme = models.CharField(max_length=32, choices=THEME_CHOICES, default=DEFAULT_THEME)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    objects = UserManager()

    def __str__(self):
        return self.email

# Create your models here.
