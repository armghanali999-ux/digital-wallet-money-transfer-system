import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from common.domain.exceptions import DomainError
from transactions.models import Transaction
from wallets.forms import MoneyForm, TransferForm, WalletForm
from wallets.models import Wallet
from wallets.services import create_wallet, deposit, transfer, withdraw


def customer_transactions(user):
    return Transaction.objects.filter(
        Q(source_wallet__owner=user) | Q(destination_wallet__owner=user)
    ).distinct()


@login_required
def dashboard(request):
    return render(request, "wallets/dashboard.html", {
        "wallets": Wallet.objects.filter(owner=request.user),
        "transactions": customer_transactions(request.user)[:5],
    })


@login_required
def wallet_create(request):
    form = WalletForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_wallet(request.user, form.cleaned_data["currency"])
            messages.success(request, "Wallet created.")
            return redirect("dashboard")
        except DomainError as exc:
            form.add_error(None, exc.message)
    return render(request, "wallets/form.html", {"form": form, "title": "Create wallet"})


def _money_view(request, operation):
    form = MoneyForm(request.POST or None, user=request.user, initial={"idempotency_key": uuid.uuid4()})
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            service = deposit if operation == "Deposit" else withdraw
            result = service(request.user, data["wallet"].id, data["amount"], data["wallet"].currency,
                             str(data["idempotency_key"]), data["description"])
            return render(request, "wallets/receipt.html", {"result": result})
        except DomainError as exc:
            form.add_error(None, exc.message)
    return render(request, "wallets/form.html", {"form": form, "title": operation})


@login_required
def deposit_web(request):
    return _money_view(request, "Deposit")


@login_required
def withdraw_web(request):
    return _money_view(request, "Withdraw")


@login_required
def transfer_web(request):
    form = TransferForm(request.POST or None, user=request.user, initial={"idempotency_key": uuid.uuid4()})
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        if request.POST.get("confirmed") != "yes":
            recipient = Wallet.objects.filter(id=data["recipient_wallet_id"]).select_related("owner").first()
            return render(request, "wallets/transfer_confirm.html", {"data": data, "recipient": recipient})
        try:
            result = transfer(request.user, data["sender_wallet"].id, data["recipient_wallet_id"],
                              data["amount"], str(data["idempotency_key"]), data["description"])
            return render(request, "wallets/receipt.html", {"result": result})
        except DomainError as exc:
            form.add_error(None, exc.message)
    return render(request, "wallets/form.html", {"form": form, "title": "Transfer money"})


@login_required
def history(request):
    queryset = customer_transactions(request.user)
    for field in ("type", "status"):
        if request.GET.get(field):
            queryset = queryset.filter(**{field: request.GET[field]})
    filters = {"reference__icontains": "reference", "amount__gte": "min_amount", "amount__lte": "max_amount",
               "created_at__date__gte": "start_date", "created_at__date__lte": "end_date"}
    for lookup, parameter in filters.items():
        if request.GET.get(parameter):
            queryset = queryset.filter(**{lookup: request.GET[parameter]})
    return render(request, "wallets/history.html", {"page": Paginator(queryset, 20).get_page(request.GET.get("page"))})


@login_required
def transaction_detail(request, reference):
    return render(request, "wallets/detail.html", {
        "transaction": get_object_or_404(customer_transactions(request.user), reference=reference)
    })
