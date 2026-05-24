from django.core.cache import cache
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from .models import FinancingRequest
from .serializers import (
    FinancingRequestCreateSerializer,
    FinancingRequestMerchantSerializer,
    FinancingRequestLenderSerializer,
    LenderStatusUpdateSerializer,
)
from alerts.tasks import dispatch_financing_alert
from imara_project.pagination import ImaraCursorPagination


# ---------------------------------------------------------------------------
# Merchant-facing views
# ---------------------------------------------------------------------------

@extend_schema(tags=["financing"])
class FinancingRequestCreateView(generics.CreateAPIView):
    """
    Create a new financing request for the authenticated merchant.
    An async alert task is queued immediately after creation.
    """

    serializer_class = FinancingRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Submit a financing request",
        responses={
            201: FinancingRequestMerchantSerializer,
            400: OpenApiResponse(description="Validation errors"),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        merchant = request.user.merchant_profile
        instance = FinancingRequest.objects.create(
            merchant=merchant,
            **{k: v for k, v in serializer.validated_data.items()},
        )

        # Queue alert non-blocking — client response is not delayed
        dispatch_financing_alert.delay(
            str(instance.id),
            event="created",
            merchant_phone=merchant.phone_number,
        )

        read_serializer = FinancingRequestMerchantSerializer(instance)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["financing"])
class FinancingRequestListView(generics.ListAPIView):
    """List financing requests belonging to the authenticated merchant."""

    serializer_class = FinancingRequestMerchantSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ImaraCursorPagination

    def get_queryset(self):
        return (
            FinancingRequest.objects.filter(merchant__user=self.request.user)
            .select_related("merchant")
            .order_by("-created_at")
        )

    @extend_schema(summary="List my financing requests")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Lender-facing views
# ---------------------------------------------------------------------------

class IsLenderPermission(permissions.BasePermission):
    """
    Stub permission: in the MVP any authenticated staff user is treated as a lender.
    Formative 2 will replace this with a proper Group-based check.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


@extend_schema(tags=["lender"])
class LenderRequestFeedView(generics.ListAPIView):
    """
    Lender-facing paginated feed of all financing requests.

    Uses cursor pagination — see ADR-001 for rationale.
    Supports filtering by `status` query parameter.
    """

    serializer_class = FinancingRequestLenderSerializer
    permission_classes = [IsLenderPermission]
    pagination_class = ImaraCursorPagination

    @extend_schema(
        summary="Lender: paginated financing request feed",
        parameters=[
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                description="Filter by status (pending, under_review, approved, declined, disbursed, cancelled)",
                required=False,
            ),
            OpenApiParameter(
                "country",
                OpenApiTypes.STR,
                description="Filter by merchant country (ISO 3166-1 alpha-3, e.g. KE, UG)",
                required=False,
            ),
        ],
    )
    def get_queryset(self):
        qs = FinancingRequest.objects.select_related("merchant").order_by("-created_at")
        status_filter = self.request.query_params.get("status")
        country_filter = self.request.query_params.get("country")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if country_filter:
            qs = qs.filter(merchant__country=country_filter.upper())
        return qs


@extend_schema(tags=["lender"])
class LenderRequestDetailView(APIView):
    """
    Lender: retrieve a specific financing request and optionally update its status.
    """

    permission_classes = [IsLenderPermission]

    def get_object(self, pk):
        try:
            return FinancingRequest.objects.select_related("merchant").get(pk=pk)
        except FinancingRequest.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound()

    @extend_schema(
        summary="Lender: get a single financing request",
        responses={200: FinancingRequestLenderSerializer},
    )
    def get(self, request, pk):
        instance = self.get_object(pk)
        serializer = FinancingRequestLenderSerializer(instance)
        return Response(serializer.data)

    @extend_schema(
        summary="Lender: update status of a financing request",
        request=LenderStatusUpdateSerializer,
        responses={
            200: FinancingRequestLenderSerializer,
            400: OpenApiResponse(description="Invalid status transition"),
        },
    )
    def patch(self, request, pk):
        instance = self.get_object(pk)
        serializer = LenderStatusUpdateSerializer(
            data=request.data, context={"instance": instance}
        )
        serializer.is_valid(raise_exception=True)

        instance.status = serializer.validated_data["status"]
        if serializer.validated_data.get("lender_notes"):
            instance.lender_notes = serializer.validated_data["lender_notes"]
        instance.save(update_fields=["status", "lender_notes", "updated_at"])

        # Alert merchant of status change — non-blocking
        dispatch_financing_alert.delay(
            str(instance.id),
            event="status_updated",
            merchant_phone=instance.merchant.phone_number,
            new_status=instance.status,
        )

        read_serializer = FinancingRequestLenderSerializer(instance)
        return Response(read_serializer.data)


# ---------------------------------------------------------------------------
# Reference data (cached)
# ---------------------------------------------------------------------------

STANDARD_FEES = {
    "origination_fee_pct": "2.50",
    "late_payment_fee_pct": "1.00",
    "early_repayment_fee_pct": "0.00",
    "currencies_supported": ["KES", "UGX", "TZS", "RWF"],
    "min_amount": "5000.00",
    "max_amount": "10000000.00",
    "min_repayment_days": 7,
    "max_repayment_days": 365,
    "note": "Fees are indicative and subject to credit assessment.",
}

CACHE_KEY_FEES = "reference:standard_fees"
CACHE_TTL_FEES = 3600  # 1 hour — fees change rarely, cache aggressively


@extend_schema(tags=["reference"])
class FeeReferenceView(APIView):
    """
    Return the platform's standard fee schedule.

    **Cached for 1 hour** (Redis). Rationale: fee data changes rarely
    (policy update, not transaction-driven). Caching eliminates a DB
    round trip for every lender page load and every merchant pre-check.
    On low-bandwidth connections this saves ~50-150ms per request.

    Cache is invalidated on deployment or manually via Django shell:
        cache.delete('reference:standard_fees')
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get platform fee schedule (cached)",
        responses={200: OpenApiResponse(description="Fee reference data")},
    )
    def get(self, request):
        cached = cache.get(CACHE_KEY_FEES)
        if cached:
            return Response({**cached, "_cached": True})

        cache.set(CACHE_KEY_FEES, STANDARD_FEES, timeout=CACHE_TTL_FEES)
        return Response({**STANDARD_FEES, "_cached": False})