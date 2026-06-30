from django.db import connection
from django.conf import settings

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_db = request.headers.get('X-Tenant-DB')
        

        if tenant_db:
            settings.DATABASES['tenant']['NAME'] = tenant_db
            connection.close()
            connection.settings_dict = settings.DATABASES['tenant']
            
        return self.get_response(request)