from rest_framework import generics, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse

from .models import Merchant
from .serializers import MerchantRegistrationSerializer, MerchantProfileSerializer


@extend_schema(tags=["merchants"])
class MerchantRegisterView(generics.CreateAPIView):
    """
    Register a new merchant and create their user account.

    This endpoint is intentionally unauthenticated so that field agents
    can onboard new merchants without prior login. Authentication tokens
    are obtained separately via /api/v1/auth/token/.
    """

    serializer_class = MerchantRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Register a new merchant",
        description=(
            "Creates a Django User and a linked Merchant profile in one request. "
            "Returns the merchant profile on success. Obtain JWT tokens separately."
        ),
        responses={
            201: MerchantProfileSerializer,
            400: OpenApiResponse(description="Validation errors"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        merchant = serializer.save()
        profile_serializer = MerchantProfileSerializer(merchant)
        return Response(profile_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["merchants"])
class MerchantProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the authenticated merchant's profile.

    PATCH is preferred for partial updates — useful on slow connections
    where only one or two fields change.
    """

    serializer_class = MerchantProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user.merchant_profile

    @extend_schema(
        summary="Get my merchant profile",
        responses={200: MerchantProfileSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update my merchant profile (partial)",
        responses={
            200: MerchantProfileSerializer,
            400: OpenApiResponse(description="Validation errors"),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)