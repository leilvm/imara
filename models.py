import uuid
from django.db import models
from django.contrib.auth.models import User


class Merchant(models.Model):
    """
    Represents a registered small merchant on the Imara platform.

    The `agent_code` field supports field-agent onboarding flows where
    an Imara field agent introduces the merchant and should be credited.
    """

    class BusinessType(models.TextChoices):
        SOLE_TRADER = "sole_trader", "Sole Trader"
        PARTNERSHIP = "partnership", "Partnership"
        LIMITED = "limited", "Limited Company"
        COOPERATIVE = "cooperative", "Cooperative"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="merchant_profile")

    # Business identity
    business_name = models.CharField(max_length=200)
    business_type = models.CharField(
        max_length=30, choices=BusinessType.choices, default=BusinessType.SOLE_TRADER
    )
    registration_number = models.CharField(max_length=100, blank=True, default="")

    # Contact
    phone_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, default="")

    # Location
    country = models.CharField(max_length=3, default="KE")  # ISO 3166-1 alpha-3
    region = models.CharField(max_length=100, blank=True, default="")
    town = models.CharField(max_length=100, blank=True, default="")

    # Field-agent reference (nullable — self-registered merchants won't have one)
    agent_code = models.CharField(max_length=50, blank=True, default="")

    # Lifecycle
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["country", "region"]),
        ]

    def __str__(self):
        return f"{self.business_name} ({self.phone_number})"