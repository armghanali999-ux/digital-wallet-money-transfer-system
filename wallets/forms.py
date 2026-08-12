from django import forms

from wallets.models import Wallet


class WalletForm(forms.Form):
    currency = forms.ChoiceField(choices=[("USD", "USD"), ("PKR", "PKR"), ("EUR", "EUR"), ("GBP", "GBP")])


class MoneyForm(forms.Form):
    wallet = forms.ModelChoiceField(queryset=Wallet.objects.none())
    amount = forms.DecimalField(max_digits=19, decimal_places=4, min_value=0.0001)
    description = forms.CharField(max_length=255, required=False)
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs); self.fields["wallet"].queryset = Wallet.objects.filter(owner=user, status=Wallet.Status.ACTIVE)


class TransferForm(forms.Form):
    sender_wallet = forms.ModelChoiceField(queryset=Wallet.objects.none())
    recipient_wallet_id = forms.IntegerField(min_value=1)
    amount = forms.DecimalField(max_digits=19, decimal_places=4, min_value=0.0001)
    description = forms.CharField(max_length=255, required=False)
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs); self.fields["sender_wallet"].queryset = Wallet.objects.filter(owner=user, status=Wallet.Status.ACTIVE)
