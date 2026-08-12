import uuid

from django import forms


class ReasonForm(forms.Form):
    reason = forms.CharField(max_length=255, widget=forms.Textarea(attrs={"rows": 3}))


class AdjustmentForm(ReasonForm):
    amount = forms.DecimalField(max_digits=19, decimal_places=4, help_text="Use a positive value to credit or negative value to debit.")
    idempotency_key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["idempotency_key"] = uuid.uuid4()
