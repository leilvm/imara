from rest_framework import serializers
from .models import FinancingRequest


class FinancingRequestCreateSerializer(serializers.ModelSerializer):
    """
    Merchant-facing create serializer.
    The merchant is derived from the request user, not submitted in the body.
    """

    class Meta:
        model = FinancingRequest
        fields = [
            "id",
            "amount_requested",
            "currency",
            "purpose",
            "repayment_period_days",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_amount_requested(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        if value > 10_000_000:
            raise serializers.ValidationError(
                "Requested amount exceeds the single-application limit (10,000,000)."
            )
        return value

    def validate_repayment_period_days(self, value):
        if value < 7:
            raise serializers.ValidationError("Minimum repayment period is 7 days.")
        if value > 365:
            raise serializers.ValidationError("Maximum repayment period is 365 days.")
        return value


class FinancingRequestMerchantSerializer(serializers.ModelSerializer):
    """Merchant-facing read serializer — excludes lender_notes."""

    class Meta:
        model = FinancingRequest
        fields = [
            "id",
            "amount_requested",
            "currency",
            "purpose",
            "repayment_period_days",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class FinancingRequestLenderSerializer(serializers.ModelSerializer):
    """
    Lender-facing read serializer.
    Includes merchant summary and lender_notes.
    Optimised for the paginated feed — merchant data is inlined to avoid
    extra round trips on slow connections.
    """

    merchant_id = serializers.UUIDField(source="merchant.id", read_only=True)
    merchant_name = serializers.CharField(source="merchant.business_name", read_only=True)
    merchant_phone = serializers.CharField(source="merchant.phone_number", read_only=True)
    merchant_country = serializers.CharField(source="merchant.country", read_only=True)

    class Meta:
        model = FinancingRequest
        fields = [
            "id",
            "merchant_id",
            "merchant_name",
            "merchant_phone",
            "merchant_country",
            "amount_requested",
            "currency",
            "purpose",
            "repayment_period_days",
            "status",
            "lender_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LenderStatusUpdateSerializer(serializers.Serializer):
    """Lender updates the status and optional notes of a financing request."""

    ALLOWED_TRANSITIONS = {
        FinancingRequest.Status.PENDING: [
            FinancingRequest.Status.UNDER_REVIEW,
            FinancingRequest.Status.DECLINED,
        ],
        FinancingRequest.Status.UNDER_REVIEW: [
            FinancingRequest.Status.APPROVED,
            FinancingRequest.Status.DECLINED,
        ],
        FinancingRequest.Status.APPROVED: [
            FinancingRequest.Status.DISBURSED,
        ],
    }

    status = serializers.ChoiceField(choices=FinancingRequest.Status.choices)
    lender_notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        instance = self.context.get("instance")
        new_status = attrs["status"]
        allowed = self.ALLOWED_TRANSITIONS.get(instance.status, [])
        if new_status not in allowed:
            raise serializers.ValidationError(
                {
                    "status": (
                        f"Cannot transition from '{instance.status}' to '{new_status}'. "
                        f"Allowed next statuses: {allowed or 'none'}."
                    )
                }
            )
        return attrs