import uuid
from django.db import models
from merchants.models import Merchant


class FinancingRequest(models.Model):
    """
    A merchant's application for working-capital financing.

    Status transitions:
        pending → under_review → approved | declined
        approved → disbursed
        any → cancelled (by merchant, before disbursement)

    The `lender_notes` field is write-once by the reviewing lender
    and never exposed in merchant-facing serializers.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"
        DISBURSED = "disbursed", "Disbursed"
        CANCELLED = "cancelled", "Cancelled"

    class Currency(models.TextChoices):
        KES = "KES", "Kenyan Shilling"
        UGX = "UGX", "Ugandan Shilling"
        TZS = "TZS", "Tanzanian Shilling"
        RWF = "RWF", "Rwandan Franc"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="financing_requests"
    )

    # Request details
    amount_requested = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.KES)
    purpose = models.TextField(help_text="Brief description of how funds will be used")
    repayment_period_days = models.PositiveIntegerField(
        default=30, help_text="Requested repayment window in days"
    )

    # Lifecycle
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    lender_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["merchant", "status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"FinancingRequest {self.id} — {self.merchant.business_name} ({self.status})"