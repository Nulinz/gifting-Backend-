from django.conf import settings
from django.db import connections
from django.contrib.auth.models import AnonymousUser
from mysite.tenant_context import (
    set_current_db_name,
    clear_current_db_name,
)

class TenantDatabaseMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        active_db = "default"

        if hasattr(request, "user") and not isinstance(request.user, AnonymousUser):
            db_name = getattr(request.user, "db_name", None)

            if db_name:
                active_db = db_name.strip().replace(" ", "_")

        if active_db != "default" and active_db not in settings.DATABASES:
            base = settings.DATABASES["default"].copy()
            base["NAME"] = active_db
            settings.DATABASES[active_db] = base

        set_current_db_name(active_db)

        print("DEBUG Tenant:", active_db)

        try:
            response = self.get_response(request)
        finally:
            clear_current_db_name()

        return response