from django.db import connection
from django.core.management import call_command
from django.conf import settings 
from rest_framework.views import APIView
from knox.models import AuthToken
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from rest_framework.response import Response
from .models import CompanyRegistry
from django.contrib.auth import get_user_model

class LoginView(APIView):
    def post(self, request):
        mobile = request.data.get('mobile_number')
        password = request.data.get('password')
        User = get_user_model()
        
        # 1. Try Master Admin Login
        user = User.objects.filter(mobile_number=mobile).first()
        if user and user.check_password(password) and user.is_superuser:
            auth_token_instance, token_string = AuthToken.objects.create(user)
            return Response({
                "role": "master", 
                "token": auth_token_instance.token_key, 
                "db": "master_registry"
            })
            
        # 2. Company Login (Fetch company FIRST, then check)
        company = CompanyRegistry.objects.filter(mobile_number=mobile).first()
        if company and company.password == password:
            # Get or create the 'bridge' user for Knox
            user, created = User.objects.get_or_create(
                username=company.mobile_number,
                defaults={'mobile_number': company.mobile_number}
            )
            
            # Pass the bridge user to Knox
            _, token_string = AuthToken.objects.create(user)
            
            return Response({
                "role": "company", 
                "token": token_string, 
                "db": company.db_name, 
                "message": "Login successful"
            })
            
        return Response({"error": "Invalid Credentials"}, status=401)    
    
class RegisterCompanyView(APIView):
    def post(self, request):
        data = request.data
        db_name = f"db_{data['company_name'].replace(' ', '_').lower()}"
        
        # 1. Save to Master Registry
        company = CompanyRegistry.objects.create(
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
            password=data.get('password')
        )
        
        # 2. Create the new database in MySQL
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            

        new_db_config = {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': db_name,
                'USER': 'root',
                'PASSWORD': 'Monika@24',
                'HOST': '127.0.0.1',
                'PORT': '3306',
                'ATOMIC_REQUESTS': False,
                'AUTOCOMMIT': True,
                'CONN_HEALTH_CHECKS': False,
                'CONN_MAX_AGE': 0,
                'OPTIONS': {},
                'TEST': {'NAME': None},
                'TIME_ZONE': 'UTC',
            }
        settings.DATABASES[db_name] = new_db_config
        
        # 4. Trigger migrations for the new database
        call_command('migrate', 'register', database=db_name)
        
        return Response({
            "message": "Company registered and database created successfully!",
            "db_name": db_name
        })