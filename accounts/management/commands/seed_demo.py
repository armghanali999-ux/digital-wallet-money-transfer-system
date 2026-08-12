import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from wallets.models import Wallet


class Command(BaseCommand):
    help = "Create safe local demonstration users and wallets without embedded passwords."

    def add_arguments(self, parser):
        parser.add_argument("--reset-passwords", action="store_true", help="Generate new passwords for existing demo users.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data can only be created when DEBUG=True.")

        created_credentials = []
        definitions = (
            ("demo.customer@example.test", "Demo Customer", User.Role.CUSTOMER, False),
            ("demo.admin@example.test", "Demo Administrator", User.Role.ADMIN, True),
        )
        users = {}
        for email, name, role, is_staff in definitions:
            user, created = User.objects.get_or_create(email=email, defaults={
                "name": name, "role": role, "status": User.Status.ACTIVE,
                "is_staff": is_staff, "is_superuser": is_staff,
            })
            if created or options["reset_passwords"]:
                password = secrets.token_urlsafe(18)
                user.set_password(password)
                user.name = name
                user.role = role
                user.status = User.Status.ACTIVE
                user.is_staff = is_staff
                user.is_superuser = is_staff
                user.save()
                created_credentials.append((email, password))
            users[role] = user

        customer = users[User.Role.CUSTOMER]
        for currency in ("USD", "PKR"):
            Wallet.objects.get_or_create(owner=customer, active_currency=currency, defaults={"currency": currency})

        self.stdout.write(self.style.SUCCESS("Demo users and customer wallets are ready."))
        if created_credentials:
            self.stdout.write("One-time local credentials (store privately; they are not written to source files):")
            for email, password in created_credentials:
                self.stdout.write(f"  {email}: {password}")
        else:
            self.stdout.write("Existing passwords were preserved. Use --reset-passwords to generate replacements.")
