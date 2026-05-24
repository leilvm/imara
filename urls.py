from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Feature apps
    path("api/v1/", include("merchants.urls")),
    path("api/v1/", include("financing.urls")),

    # OpenAPI schema and docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

from django.urls import path
from .views import MerchantRegisterView, MerchantProfileView

urlpatterns = [
    path("merchants/register/", MerchantRegisterView.as_view(), name="merchant-register"),
    path("merchants/me/", MerchantProfileView.as_view(), name="merchant-profile"),
]