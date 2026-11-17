from django import forms

from core.forms import BootstrapFormMixin

from .models import Category, Product


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    """
    On *create* the form includes the opening quantity.
    On *edit* the quantity is not editable: stock must change via Stock In / Stock Out
    so that the stock history stays accurate.
    """

    class Meta:
        model = Product
        fields = (
            "name",
            "code",
            "category",
            "purchase_price",
            "selling_price",
            "quantity",
            "min_stock_level",
            "description",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "purchase_price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "selling_price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "quantity": forms.NumberInput(attrs={"min": "0"}),
            "min_stock_level": forms.NumberInput(attrs={"min": "0"}),
        }
        labels = {"quantity": "Opening quantity"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            del self.fields["quantity"]
        else:
            self.fields["quantity"].initial = 0
            self.fields["quantity"].help_text = "Initial stock on hand (recorded as opening stock)."

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        qs = Product.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A product with this code already exists.")
        return code

    def clean(self):
        cleaned = super().clean()
        purchase, selling = cleaned.get("purchase_price"), cleaned.get("selling_price")
        if purchase is not None and selling is not None and selling < purchase:
            self.add_error("selling_price", "Selling price is lower than purchase price (you would sell at a loss).")
        return cleaned
