from django.contrib import admin
from .models import Merchant


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ["business_name", "phone_number", "country", "is_verified", "created_at"]
    list_filter = ["is_verified", "business_type", "country"]
    search_fields = ["business_name", "phone_number", "user__username"]
    readonly_fields = ["id", "created_at", "updated_at"]