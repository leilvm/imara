from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from imara_project.permissions import IsMerchantOwnerOrStaff
from .models import LoanApplication
from .serializers import LoanApplicationSerializer

class LoanApplicationViewSet(viewsets.ModelViewSet):
    """
    Hardened Endpoint verifying programmatic isolation and data boundaries.
    """
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated, IsMerchantOwnerOrStaff]

    def get_queryset(self):
        """
        Enforce data segmentation at the query level. Staff and Compliance users 
        can access the complete global registry; merchants are isolated strictly to their historical pipeline.
        """
        user = self.request.user
        if user.is_staff or getattr(user, 'is_compliance', False):
            return LoanApplication.objects.all()
            
        # Strict context-aware horizontal restriction
        return LoanApplication.objects.filter(merchant__merchant_user=user)

    def perform_create(self, serializer):
        # Automatically attach the creating user context to maintain traceable accountability trails
        serializer.save(created_by=self.request.user)