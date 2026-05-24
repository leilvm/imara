from django.urls import path
from .views import (
    FinancingRequestCreateView,
    FinancingRequestListView,
    LenderRequestFeedView,
    LenderRequestDetailView,
    FeeReferenceView,
)

urlpatterns = [
    # Merchant-facing
    path("financing/", FinancingRequestCreateView.as_view(), name="financing-create"),
    path("financing/mine/", FinancingRequestListView.as_view(), name="financing-list"),

    # Lender-facing
    path("lender/requests/", LenderRequestFeedView.as_view(), name="lender-feed"),
    path("lender/requests/<uuid:pk>/", LenderRequestDetailView.as_view(), name="lender-detail"),

    # Reference (cached)
    path("reference/fees/", FeeReferenceView.as_view(), name="reference-fees"),
]