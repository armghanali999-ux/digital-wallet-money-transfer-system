from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User
from administration.forms import AdjustmentForm, ReasonForm
from administration.models import AdministrativeAudit
from common.domain.exceptions import DomainError
from transactions.models import Transaction
from wallets.models import Wallet
from wallets.services import adjust_balance, set_wallet_frozen


def administrator_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not (request.user.is_staff or request.user.role == User.Role.ADMIN):
            return render(request, "403.html", status=403)
        return view(request, *args, **kwargs)
    return wrapped


@administrator_required
def admin_dashboard(request):
    return render(request, "administration/dashboard.html", {
        "user_count": User.objects.count(), "wallet_count": Wallet.objects.count(),
        "transaction_count": Transaction.objects.count(),
        "failed_count": Transaction.objects.filter(status=Transaction.Status.FAILED).count(),
        "recent_audits": AdministrativeAudit.objects.select_related("administrator", "wallet")[:5],
    })


@administrator_required
def user_list(request):
    users = User.objects.all().order_by("-created_at")
    if request.GET.get("q"): users = users.filter(Q(email__icontains=request.GET["q"]) | Q(name__icontains=request.GET["q"]))
    return render(request, "administration/users.html", {"page": Paginator(users, 20).get_page(request.GET.get("page"))})


@administrator_required
def wallet_list(request):
    wallets = Wallet.objects.select_related("owner").all().order_by("-created_at")
    query = request.GET.get("q", "").strip()
    if query:
        search = Q(owner__email__icontains=query)
        if query.isdigit():
            search |= Q(id=int(query))
        wallets = wallets.filter(search)
    return render(request, "administration/wallets.html", {"page": Paginator(wallets, 20).get_page(request.GET.get("page"))})


@administrator_required
def wallet_detail(request, pk):
    wallet = get_object_or_404(Wallet.objects.select_related("owner"), id=pk)
    transactions = Transaction.objects.filter(Q(source_wallet=wallet) | Q(destination_wallet=wallet)).distinct()[:20]
    return render(request, "administration/wallet_detail.html", {
        "wallet": wallet, "transactions": transactions,
        "audits": wallet.admin_audits.select_related("administrator")[:20],
        "status_form": ReasonForm(), "adjustment_form": AdjustmentForm(),
    })


def _status_action(request, pk, freeze):
    form = ReasonForm(request.POST)
    if form.is_valid():
        try:
            set_wallet_frozen(request.user, pk, freeze, form.cleaned_data["reason"])
            messages.success(request, "Wallet status updated and audited.")
        except DomainError as exc: messages.error(request, exc.message)
    else: messages.error(request, "A reason is required.")
    return redirect("administration-wallet-detail", pk=pk)


@administrator_required
@require_POST
def freeze_wallet(request, pk):
    return _status_action(request, pk, True)


@administrator_required
@require_POST
def unfreeze_wallet(request, pk):
    return _status_action(request, pk, False)


@administrator_required
@require_POST
def adjust_wallet(request, pk):
    form = AdjustmentForm(request.POST)
    if form.is_valid():
        try:
            adjust_balance(request.user, pk, form.cleaned_data["amount"], form.cleaned_data["reason"], str(form.cleaned_data["idempotency_key"]))
            messages.success(request, "Balance adjustment completed and audited.")
        except DomainError as exc: messages.error(request, exc.message)
    else: messages.error(request, "Enter a valid signed amount and mandatory reason.")
    return redirect("administration-wallet-detail", pk=pk)


@administrator_required
def failed_transactions(request):
    transactions = Transaction.objects.filter(status=Transaction.Status.FAILED).select_related("source_wallet", "destination_wallet").order_by("-created_at")
    if request.GET.get("code"): transactions = transactions.filter(failure_code__icontains=request.GET["code"])
    return render(request, "administration/failed_transactions.html", {"page": Paginator(transactions, 20).get_page(request.GET.get("page"))})


@administrator_required
def audit_history(request):
    audits = AdministrativeAudit.objects.select_related("administrator", "wallet", "transaction")
    return render(request, "administration/audits.html", {"page": Paginator(audits, 20).get_page(request.GET.get("page"))})
