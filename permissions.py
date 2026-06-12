from rest_framework import permissions

class IsMerchantOwnerOrStaff(permissions.BasePermission):
    """
    Object-level authorization to ensure merchants only see their own records,
    while permitting compliance/staff users broad access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Staff and Compliance officers bypass explicit owner validation
        if request.user.is_staff or getattr(request.user, 'is_compliance', False):
            return True
            
        # Standard Data-Aware cross-checking
        # Validates if the object itself is a Merchant, or belongs structurally to one
        if hasattr(obj, 'merchant_user'):
            return obj.merchant_user == request.user
        elif hasattr(obj, 'merchant'):
            return obj.merchant.merchant_user == request.user
            
        return False