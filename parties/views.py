import csv
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from knox.auth import TokenAuthentication
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import HttpResponse
import pandas as pd
from .models import customer, contact_person , vendor
from .serializers import CustomerSerializer, ContactPersonSerializer ,VendorSerializer 
from mysite.tenant_context import get_current_db_name , set_current_db_name
from mysite.db_utils import connect_to_db

class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    # Dynamically fetched for each request to bypass global initialization caches
  
    # def get_queryset(self):
    #     active_db = self.request.user.db_name.strip().replace(" ", "_")

    #     # Register the tenant connection if it doesn't exist
    #     if active_db not in connections.databases:
    #         config = settings.DATABASES["default"].copy()
    #         config["NAME"] = active_db
    #         connections.databases[active_db] = config
    #     set_current_db_name(active_db)
    #     return customer.objects.using(active_db).all()
    
    def get_queryset(self):
        active_db = self.request.user.db_name.strip().replace(" ", "_")
        connect_to_db(active_db) # Call the helper
        return customer.objects.using(active_db).all()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        customer_obj = self.get_object()
        active_db = get_current_db_name()
        contacts = contact_person.objects.using(active_db).filter(customer=customer_obj)
        serializer = ContactPersonSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        active_tenant_db = get_current_db_name()
        
        with transaction.atomic(using=active_tenant_db):
            for _, row in df.iterrows():
                customer_data = {
                    "customer_code": row['customer_code'],
                    "name": row['name'],
                    "email": str(row['email']) if pd.notna(row['email']) else None,
                    "mobile": str(row['mobile']) if pd.notna(row['mobile']) else None,
                    "address": {
                        "line1": row['line1'],
                        "city": row['city'],
                        "state": row['state'],
                        "pincode": row['pincode']
                    }
                }
                
                # Pass the request context down to bulk uploads so validators see the tenant DB configuration
                serializer = CustomerSerializer(data=customer_data, context={'request': request})
                
                if serializer.is_valid():
                    # FIXED: Removed (using=active_tenant_db) here as well
                    serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Bulk upload successful!"}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        active_db = request.user.db_name.strip().replace(" ", "_")
        connect_to_db(active_db)
        customer_obj = get_object_or_404(customer.objects.using(active_db), pk=pk)
        with transaction.atomic(using=active_db):
            customer_obj.status = 'Inactive' if customer_obj.status == 'Active' else 'Active'
            customer_obj.save(using=active_db)
        return Response({'status': customer_obj.status})
    
    @action(detail=False, methods=['get'])
    def download_template(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Template.csv"'
        writer = csv.writer(response)
        writer.writerow(['customer_code', 'name', 'email', 'mobile', 'line1', 'city', 'state', 'pincode'])
        return response


class ContactPersonViewSet(viewsets.ModelViewSet):
    serializer_class = ContactPersonSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        active_db = self.request.user.db_name.strip().replace(" ", "_")
        connect_to_db(active_db) 
        return contact_person.objects.using(active_db).all()

class VendorViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        active_db = self.request.user.db_name.strip().replace(" ", "_")
        connect_to_db(active_db) 
        return vendor.objects.using(active_db).all()
    
    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()
        
    @action(detail=True, methods=['get'])
    def contacts(self, request, pk=None):
        vendor_obj = self.get_object()
        active_db = get_current_db_name()
        contacts = contact_person.objects.using(active_db).filter(vendor_code=vendor_obj.id)
        serializer = ContactPersonSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        file = request.FILES.get('file')
        if not file: return Response({"error": "No file"}, status=400)
        
        try:
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        active_db = get_current_db_name()
        with transaction.atomic(using=active_db):
            for _, row in df.iterrows():
                data = {
                    "vendor_code": row['vendor_code'],
                    "name": row['name'],
                    "address": {"line1": row['line1'], "city": row['city'], "state": row['state'], "pincode": row['pincode']}
                }
                serializer = VendorSerializer(data=data, context={'request': request})
                if serializer.is_valid():
                    serializer.save()
                else:
                    return Response(serializer.errors, status=400)
        return Response({"message": "Bulk upload successful!"}, status=201)
    
    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        active_db = request.user.db_name.strip().replace(" ", "_")
        connect_to_db(active_db)
        vendor_obj = get_object_or_404(vendor.objects.using(active_db),pk=pk)
        with transaction.atomic(using=active_db):
            vendor_obj.status = 'Inactive' if vendor_obj.status == 'Active' else 'Active'
            vendor_obj.save(using=active_db)
        return Response({'status': vendor_obj.status})

    @action(detail=False, methods=['get'])
    def download_template(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Vendor_Template.csv"'
        writer = csv.writer(response)
        writer.writerow(['vendor_code', 'name', 'email', 'mobile', 'line1', 'city', 'state', 'pincode'])
        return response