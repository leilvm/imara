from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Merchant

class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ['id', 'business_name', 'email', 'tax_id', 'bank_account_number', 'created_at']

    def to_representation(self, instance):
        """
        Dynamically mask sensitive records based on actor scope to maintain 
        privacy compliance metrics.
        """
        representation = super().to_representation(instance)
        request = self.context.get('request')
        
        if request and request.user:
            # Mask sensitive data fields if the user is a standard merchant partner
            if not request.user.is_staff and not getattr(request.user, 'is_compliance', False):
                representation['tax_id'] = self.mask_sensitive_field(representation.get('tax_id'))
                representation['bank_account_number'] = self.mask_sensitive_field(representation.get('bank_account_number'))
                
        return representation

    def mask_sensitive_field(self, value):
        if not value:
            return ""
        value_str = str(value)
        if len(value_str) <= 4:
            return "****"
        return f"{'*' * (len(value_str) - 4)}{value_str[-4:]}"