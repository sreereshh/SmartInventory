from django import forms

from core.forms import BootstrapFormMixin

from .models import Customer


class CustomerForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = ("name", "phone", "email", "address")
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}
