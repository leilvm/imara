from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Merchant


class MerchantRegistrationSerializer(serializers.Serializer):
    """
    Handles new merchant registration including User creation.
    Separate from the profile serializer so write and read shapes
    are explicit and we can validate uniqueness cleanly.
    """

    # User credentials
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})

    # Business identity
    business_name = serializers.CharField(max_length=200)
    business_type = serializers.ChoiceField(
        choices=Merchant.BusinessType.choices, default=Merchant.BusinessType.SOLE_TRADER
    )
    registration_number = serializers.CharField(max_length=100, required=False, default="")

    # Contact
    phone_number = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, default="")

    # Location
    country = serializers.CharField(max_length=3, default="KE")
    region = serializers.CharField(max_length=100, required=False, default="")
    town = serializers.CharField(max_length=100, required=False, default="")

    # Field agent
    agent_code = serializers.CharField(max_length=50, required=False, default="")

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_phone_number(self, value):
        # Normalise: strip spaces, require + prefix for international numbers
        value = value.replace(" ", "")
        if Merchant.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            email=validated_data.get("email", ""),
        )
        merchant = Merchant.objects.create(
            user=user,
            business_name=validated_data["business_name"],
            business_type=validated_data.get("business_type", Merchant.BusinessType.SOLE_TRADER),
            registration_number=validated_data.get("registration_number", ""),
            phone_number=validated_data["phone_number"],
            email=validated_data.get("email", ""),
            country=validated_data.get("country", "KE"),
            region=validated_data.get("region", ""),
            town=validated_data.get("town", ""),
            agent_code=validated_data.get("agent_code", ""),
        )
        return merchant


class MerchantProfileSerializer(serializers.ModelSerializer):
    """Read/update view of a merchant profile. Username is read-only."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Merchant
        fields = [
            "id",
            "username",
            "business_name",
            "business_type",
            "registration_number",
            "phone_number",
            "email",
            "country",
            "region",
            "town",
            "agent_code",
            "is_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "username", "is_verified", "created_at", "updated_at"]