from rest_framework import status, generics, permissions
from rest_framework.response import Response
from django.db import transaction, connection
from django.core.management import call_command
from django.conf import settings
from knox.views import LoginView as KnoxLoginView
from knox.models import AuthToken # Added this import
from .models import company_register, register_employee
from .serializers import CompanyRegistrationSerializer
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed

from django.db import connections

from mysite.tenant_context import set_current_db_name, clear_current_db_name # Ensure these are imported

def provision_tenant_database(db_name):
    # 1. Create the physical database
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;")
    
    # 2. Dynamically update Django settings
    if db_name not in settings.DATABASES:
        base_config = settings.DATABASES['default'].copy()
        base_config['NAME'] = db_name
        settings.DATABASES[db_name] = base_config
        connections.configure_settings(settings.DATABASES)

    # 3. SET THE CONTEXT so the Router knows where to allow the migration
    set_current_db_name(db_name)
    
    try:
        # 4. Apply migrations
        call_command('migrate', 'contenttypes', database=db_name, interactive=False, verbosity=0)
        call_command('migrate', 'parties', database=db_name, interactive=False, verbosity=0)
    finally:
        # 5. ALWAYS clear the context after finishing
        clear_current_db_name()


class CompanyRegistrationView(generics.CreateAPIView):
    """
    Endpoint for a new Company Registration.
    Creates records in Master tables and provisions an isolated database.
    """
    serializer_class = CompanyRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        db_name = data['db_name']

        try:
            # 1. Force atomicity ONLY for writes to Master ('default') tables
            with transaction.atomic(using='default'):
                
                # Save data into the Master Company register table
                company_register.objects.create(
                    full_name=data['full_name'],
                    email=data['email'],
                    mobile_number=data['mobile_number'],
                    company_name=data['company_name'],
                    db_name=db_name,
                    gst_number=data['gst_number'],
                    pan_number=data['pan_number'],
                    address=data['address'],
                    city=data['city'],
                    state=data['state'],
                    pincode=data['pincode'],
                    password=data['password']
                )

                # Create the owner profile as the first entry in the Master Employee table
                register_employee.objects.create_user(
                    mobile_number=data['mobile_number'],
                    employee_name=data['full_name'],
                    company_name=data['company_name'],
                    db_name=db_name,
                    password=data['password']
                )

            # 2. FIXED: Create the database and migrate AFTER master records are safely committed
            provision_tenant_database(db_name)

            return Response(
                {
                    "status": "Success", 
                    "message": f"Company registered and database '{db_name}' initialized successfully."
                }, 
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {"error": f"Registration workflow failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TenantLoginView(KnoxLoginView):
    """
    Login endpoint utilizing DRF Knox.
    Accepts JSON body payload (mobile_number and password) from Postman,
    authenticates the profile, and returns a secure Knox Token.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # Clear BasicAuthentication to accept raw JSON payloads

    def post(self, request, format=None):
        mobile_number = request.data.get("mobile_number")
        password = request.data.get("password")

        if not mobile_number or not password:
            raise AuthenticationFailed("Both mobile_number and password fields are required.")

        # Authenticate against your custom user model tracking system
        user = authenticate(request, username=mobile_number, password=password)

        if user is None:
            raise AuthenticationFailed("Invalid mobile number or password.")

        instance, token = AuthToken.objects.create(user)
        
        return Response({
            "status": "Success",
            "token": token,
            "expiry": instance.expiry,
            "user": {
                "mobile_number": user.mobile_number,
                "employee_name": user.employee_name,
                "db_name": user.db_name
            }
        }, status=status.HTTP_200_OK)