from django import forms

from core.forms import BootstrapFormMixin
from products.models import Product

from .models import StockTransaction

IN_REASONS = [
    (StockTransaction.Reason.PURCHASE, "Purchase / restock"),
    (StockTransaction.Reason.RETURN, "Customer return"),
    (StockTransaction.Reason.ADJUSTMENT, "Adjustment / correction"),
    (StockTransaction.Reason.OTHER, "Other"),
]
OUT_REASONS = [
    (StockTransaction.Reason.DAMAGE, "Damaged / expired"),
    (StockTransaction.Reason.ADJUSTMENT, "Adjustment / correction"),
    (StockTransaction.Reason.OTHER, "Other"),
]


class StockMovementForm(BootstrapFormMixin, forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={"min": "1"}))
    reason = forms.ChoiceField(choices=[])
    note = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={"placeholder": "Optional note"}))

    def __init__(self, *args, transaction_type=StockTransaction.Type.IN, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction_type = transaction_type
        self.fields["product"].queryset = Product.objects.order_by("name")
        self.fields["product"].label_from_instance = lambda p: f"{p.name} ({p.code}) – stock: {p.quantity}"
        self.fields["reason"].choices = IN_REASONS if transaction_type == StockTransaction.Type.IN else OUT_REASONS

    def clean(self):
        cleaned = super().clean()
        product, qty = cleaned.get("product"), cleaned.get("quantity")
        if self.transaction_type == StockTransaction.Type.OUT and product and qty and qty > product.quantity:
            self.add_error(
                "quantity",
                f"Insufficient stock: only {product.quantity} unit(s) of {product.name} available.",
            )
        return cleaned
