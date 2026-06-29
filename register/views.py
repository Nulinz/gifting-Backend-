import os
from django.db import connection
from django.core.management import call_command
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CompanyRegistry

class RegisterCompanyView(APIView):
    def post(self, request):
        data = request.data
        # Generate a safe DB name: 'db_' + company name (lowercase, no spaces)
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
            pincode=data['pincode']
        )
        
        # 2. Programmatically create the new database
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {db_name}")
            
        # 3. Trigger migrations for the new database
        # This creates all your tables (Enquiry, Campaign, etc.) inside the new DB
        call_command('migrate', database=db_name) 
        
        return Response({
            "message": "Company registered and database created successfully!",
            "db_name": db_name
        })