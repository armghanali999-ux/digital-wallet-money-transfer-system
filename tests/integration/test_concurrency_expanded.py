from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections

from accounts.models import User
from common.domain.exceptions import DomainError
from transactions.models import Transaction, WalletTransaction
from wallets.models import Wallet
from wallets.services import deposit, transfer, withdraw


pytestmark = pytest.mark.django_db(transaction=True)


def run_threaded(callables):
    barrier = Barrier(len(callables))
    def run(function):
        close_old_connections(); barrier.wait()
        try: return ("ok", function())
        except Exception as exc: return ("error", exc)
        finally: close_old_connections()
    with ThreadPoolExecutor(max_workers=len(callables)) as executor:
        return list(executor.map(run, callables))


def test_concurrent_withdrawals_cannot_overspend():
    user = User.objects.create_user(email="concurrent-withdraw@example.com", name="Concurrent", password="StrongPass123!")
    wallet = Wallet.objects.create(owner=user, currency="USD", balance=Decimal("100"))
    def operation(key):
        return lambda: withdraw(User.objects.get(id=user.id), wallet.id, "80", "USD", key)
    results = run_threaded([operation("withdraw-a"), operation("withdraw-b")])
    wallet.refresh_from_db()
    assert [status for status, _ in results].count("ok") == 1
    assert wallet.balance == Decimal("20.0000")
    assert Transaction.objects.filter(type="WITHDRAWAL", status="COMPLETED").count() == 1
    assert Transaction.objects.filter(type="WITHDRAWAL", status="FAILED").count() == 1


def test_concurrent_identical_deposits_process_once():
    user = User.objects.create_user(email="concurrent-idem@example.com", name="Concurrent", password="StrongPass123!")
    wallet = Wallet.objects.create(owner=user, currency="USD")
    operation = lambda: deposit(User.objects.get(id=user.id), wallet.id, "25", "USD", "concurrent-same-key")
    results = run_threaded([operation, operation])
    wallet.refresh_from_db()
    assert [status for status, _ in results] == ["ok", "ok"]
    assert results[0][1] == results[1][1]
    assert wallet.balance == Decimal("25.0000")
    assert Transaction.objects.filter(type="DEPOSIT").count() == 1


def test_simultaneous_opposing_transfers_use_deterministic_locks():
    first = User.objects.create_user(email="concurrent-a@example.com", name="A", password="StrongPass123!")
    second = User.objects.create_user(email="concurrent-b@example.com", name="B", password="StrongPass123!")
    first_wallet = Wallet.objects.create(owner=first, currency="USD", balance=Decimal("100"))
    second_wallet = Wallet.objects.create(owner=second, currency="USD", balance=Decimal("100"))
    operations = [
        lambda: transfer(User.objects.get(id=first.id), first_wallet.id, second_wallet.id, "10", "opposing-a"),
        lambda: transfer(User.objects.get(id=second.id), second_wallet.id, first_wallet.id, "10", "opposing-b"),
    ]
    results = run_threaded(operations)
    first_wallet.refresh_from_db(); second_wallet.refresh_from_db()
    assert [status for status, _ in results].count("ok") == 2
    assert first_wallet.balance == second_wallet.balance == Decimal("100.0000")
    assert Transaction.objects.filter(type="TRANSFER", status="COMPLETED").count() == 2
    assert WalletTransaction.objects.filter(transaction__type="TRANSFER").count() == 4
