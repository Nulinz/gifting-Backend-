from django.conf import settings
from django.db import connections
from knox.auth import TokenAuthentication
from mysite.tenant_context import set_current_db_name, clear_current_db_name
import traceback

class TenantDatabaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        print("\n=== [MIDDLEWARE DEBUG START] ===")
        print(f"Incoming Path: {request.path}")
        print(f"Authorization Header Found: '{auth_header}'")
        
        if auth_header and auth_header.startswith('Token '):
            try:
                knox_auth = TokenAuthentication()
                print("Attempting Knox Token verification...")
                auth_result = knox_auth.authenticate(request)
                
                if auth_result is not None:
                    user = auth_result[0]
                    db_name = getattr(user, 'db_name', None)
                    print(f"Knox Auth Success! User: {user.mobile_number}, Model db_name field value: '{db_name}'")
                    
                    if db_name:
                        db_config_key = db_name.strip().replace(" ", "_")
                        print(f"Switching Thread Database Context to target: '{db_config_key}'")
                        
                        set_current_db_name(db_config_key)
                        
                        if db_config_key not in settings.DATABASES:
                            print(f"Database '{db_config_key}' not discovered in settings. Injecting configuration properties dynamic setup...")
                            base_config = settings.DATABASES['default'].copy()
                            base_config['NAME'] = db_config_key
                            settings.DATABASES[db_config_key] = base_config
                            connections.ensure_defaults(db_config_key)
                        
                        print("Proceeding to View layer under Tenant Connection...")
                        response = self.get_response(request)
                        clear_current_db_name()
                        print("=== [MIDDLEWARE DEBUG END] ===\n")
                        return response
                    else:
                        print("CRITICAL: User authenticated successfully, but their profile 'db_name' text field is empty/blank!")
                else:
                    print("Knox Auth returned None! Token might be invalid or expired.")
                    
            except Exception as e:
                print(f"Knox authentication validation crashed with error: {str(e)}")
                traceback.print_exc()
                
        print("Fallback warning: No matching token context found. Routing request to 'default' (master_registry)")
        set_current_db_name('default')
        response = self.get_response(request)
        clear_current_db_name()
        print("=== [MIDDLEWARE DEBUG END] ===\n")
        return response