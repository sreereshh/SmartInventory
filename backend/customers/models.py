from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r"^[0-9+\-\s()]{7,20}$",
    message="Enter a valid phone number (digits, spaces, +, -, parentheses; 7-20 characters).",
)


class Customer(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, validators=[phone_validator])
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.name
