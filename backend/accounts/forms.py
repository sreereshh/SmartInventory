from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from core.forms import BootstrapFormMixin

from .models import User


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"placeholder": "Username", "autofocus": True})
        self.fields["password"].widget.attrs.update({"placeholder": "Password"})


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    """Public registration always creates a *Staff* account. Admins promote users later."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STAFF
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserManageForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "role", "is_active")
        widgets = {"is_active": forms.CheckboxInput()}
