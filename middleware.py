import json
import logging
from django.utils.timezone import now

logger = logging.getLogger('compliance_audit')

class AuditLogMiddleware:
    """
    Automated interceptor that generates structured audit trails for access to 
    sensitive financial operations and PII endpoints.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Scrape sensitive path indicators
        path = request.path.lower()
        sensitive_keywords = ['financing', 'merchants', 'loans', 'payouts', 'alerts']
        
        if any(keyword in path for keyword in sensitive_keywords) and request.user.is_authenticated:
            audit_entry = {
                "timestamp": now().isoformat(),
                "actor_id": request.user.id,
                "username": request.user.username,
                "role": "staff/compliance" if request.user.is_staff else "merchant_partner",
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "client_ip": self.get_client_ip(request)
            }
            # Log output ensuring structured, clean formatting (JSON)
            logger.info(json.dumps(audit_entry))
            
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')