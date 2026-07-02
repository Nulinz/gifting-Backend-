from rest_framework import serializers
from .models import (customer, contact_person, address , vendor ,
vendor_contact_person, Employee , EmployeePermission)
from register.models import register_employee
from mysite.tenant_context import get_current_db_name
from django.conf import settings
from django.db import connections
from mysite.tenant_context import get_current_db_name ,set_current_db_name, clear_current_db_name
from django.db import transaction
from mysite.db_utils import connect_to_db


class TenantSerializerMixin(serializers.ModelSerializer):
    def get_active_db(self):
        return 'tenant'
    
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = address
        exclude = ['entity_type', 'entity_id']


class ContactPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = contact_person
        fields = ['id', 'name', 'department', 'role', 'email', 'mobile','status', 'created_by', 'created_at', 'updated_at']


class CustomerSerializer(serializers.ModelSerializer):
    address = AddressSerializer(write_only=True)
    contacts = ContactPersonSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = customer
        fields = ['id', 'customer_code', 'name', 'email', 'mobile', 'gst_no', 'remarks', 'status', 'created_by', 'created_at', 'updated_at', 'address', 'contacts']
        extra_kwargs = {
            'customer_code': {'validators': []},
            'email': {'validators': []}
        }

    def validate_customer_code(self, value):
        if not value:
            return value
        request = self.context.get('request')
        active_db = 'default'
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_db = getattr(request.user, 'db_name', None)
            if user_db:
                active_db = user_db.strip().replace(" ", "_")

        if active_db != 'default' and active_db not in settings.DATABASES:
            base_config = settings.DATABASES['default'].copy()
            base_config['NAME'] = active_db
            settings.DATABASES[active_db] = base_config
            connections.configure_settings(settings.DATABASES)

        instance_id = self.instance.id if self.instance else None
        queryset = customer.objects.using(active_db).filter(customer_code=value)
        
        if instance_id:
            queryset = queryset.exclude(id=instance_id)
        if queryset.exists():
            raise serializers.ValidationError("A customer with this customer code already exists.")
        return value

    def validate_email(self, value):
        if not value:
            return value
        request = self.context.get('request')
        active_db = 'default'
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_db = getattr(request.user, 'db_name', None)
            if user_db:
                active_db = user_db.strip().replace(" ", "_")

        # 2. Inject configuration properties if missing 
        if active_db != 'default' and active_db not in settings.DATABASES:
            base_config = settings.DATABASES['default'].copy()
            base_config['NAME'] = active_db
            settings.DATABASES[active_db] = base_config
            connections.configure_settings(settings.DATABASES)

        instance_id = self.instance.id if self.instance else None
        
        # 3. FORCE the query to check your tenant database instead of master_registry
        queryset = customer.objects.using(active_db).filter(email=value)
        
        if instance_id:
            queryset = queryset.exclude(id=instance_id)
        if queryset.exists():
            raise serializers.ValidationError("A customer with this email address already exists.")
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        active_db = 'default'
        creator_name = getattr(request.user, 'employee_name', 'System')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_db = getattr(request.user, 'db_name', None)
            if user_db:
                active_db = user_db.strip().replace(" ", "_")

        set_current_db_name(active_db)

        try:
            address_data = validated_data.pop('address')
            contacts_data = validated_data.pop('contacts', [])
            
            customer_obj = customer.objects.db_manager(active_db).create(
                created_by=creator_name, 
                **validated_data
            )
            customer_obj._state.db = active_db

            address.objects.db_manager(active_db).create(
                entity_type='customer', 
                entity_id=customer_obj.id, 
                created_by=creator_name,
                **address_data
            )
            
            for contact in contacts_data:
                contact_person.objects.db_manager(active_db).create(
                    customer_id=customer_obj.id, 
                    created_by=creator_name, 
                    **contact
                )
                
            # Explicitly force the instance to remember its database connection
            customer_obj._state.db = active_db
            return customer_obj
            
        finally:
            clear_current_db_name()
            
    def update(self, instance, validated_data):
        active_db = get_current_db_name()
        address_data = validated_data.pop('address', None)
        
        # Explicitly update instance values
        instance.name = validated_data.get('name', instance.name)
        instance.email = validated_data.get('email', instance.email)
        instance.mobile = validated_data.get('mobile', instance.mobile)
        instance.gst_no = validated_data.get('gst_no', instance.gst_no)
        instance.remarks = validated_data.get('remarks', instance.remarks)
        instance.status = validated_data.get('status', instance.status)
        
        # Save modifications to the matching tenant DB
        instance.save(using=active_db)
        
        if address_data:
            addr_obj, _ = address.objects.db_manager(active_db).get_or_create(
                entity_type='customer', 
                entity_id=instance.id
            )
            for attr, value in address_data.items():
                setattr(addr_obj, attr, value)
            addr_obj.save(using=active_db)
            
        return instance
    
    def to_representation(self, instance):
        # 1. Run the base serialization safely
        ret = super().to_representation(instance)
        
        # 2. Check if the instance itself specifies a database, otherwise fall back to thread context
        active_db = getattr(instance, '_state', None) and getattr(instance._state, 'db', None)
        if not active_db or active_db == 'default':
            active_db = get_current_db_name()

        # 3. Explicitly search the address database table for this entity matching the tenant context
        try:
            addr_obj = address.objects.db_manager(active_db).get(
                entity_type='customer',
                entity_id=instance.id
            )
            ret['address'] = AddressSerializer(addr_obj).data
        except address.DoesNotExist:
            ret['address'] = None

        # 4. Explicitly fetch and append the contacts array matching this client context
        contacts_qs = contact_person.objects.db_manager(active_db).filter(customer_id=instance.id)
        ret['contacts'] = ContactPersonSerializer(contacts_qs, many=True).data

        return ret
    
class VendorSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    address = AddressSerializer(write_only=True)
    contacts = ContactPersonSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = vendor
        fields = ['id', 'vendor_code', 'name', 'email', 'mobile', 'gst_no', 'remarks', 'status', 'created_by', 'created_at', 'updated_at','address', 'contacts']
        extra_kwargs = {
            'vendor_code': {'validators': []},
            'email': {'validators': []}
        }
        
    def validate_vendor_code(self, value):
        if not value:
            return value

        request = self.context.get('request')
        active_db = 'default'
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_db = getattr(request.user, 'db_name', None)
            if user_db:
                active_db = user_db.strip().replace(" ", "_")

        if active_db != 'default' and active_db not in settings.DATABASES:
            base_config = settings.DATABASES['default'].copy()
            base_config['NAME'] = active_db
            settings.DATABASES[active_db] = base_config
            connections.configure_settings(settings.DATABASES)

        instance_id = self.instance.id if self.instance else None
        queryset = vendor.objects.using(active_db).filter(vendor_code=value)
        
        if instance_id:
            queryset = queryset.exclude(id=instance_id)
        if queryset.exists():
            raise serializers.ValidationError("A vendor with this vendor code already exists.")
        return value

    def validate_email(self, value):
        if not value:
            return value
        request = self.context.get('request')
        active_db = 'default'
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_db = getattr(request.user, 'db_name', None)
            if user_db:
                active_db = user_db.strip().replace(" ", "_")

        # 2. Inject configuration properties if missing 
        if active_db != 'default' and active_db not in settings.DATABASES:
            base_config = settings.DATABASES['default'].copy()
            base_config['NAME'] = active_db
            settings.DATABASES[active_db] = base_config
            connections.configure_settings(settings.DATABASES)

        instance_id = self.instance.id if self.instance else None
        
        # 3. FORCE the query to check your tenant database instead of master_registry
        queryset = vendor.objects.using(active_db).filter(email=value)
        
        if instance_id:
            queryset = queryset.exclude(id=instance_id)
        if queryset.exists():
            raise serializers.ValidationError("A vendor with this email address already exists.")
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        active_db = self.context['request'].user.db_name.strip().replace(" ", "_")
        creator_name = getattr(request.user, 'employee_name', 'System')
        
        # 2. Register it dynamically
        connect_to_db(active_db) 
        
        try:
            address_data = validated_data.pop('address')
            contacts_data = validated_data.pop('contacts', [])
            
            # 3. Use active_db everywhere
            with transaction.atomic(using=active_db):
                vendor_obj = vendor.objects.db_manager(active_db).create(created_by=creator_name, **validated_data)
                
                address.objects.db_manager(active_db).create(
                    entity_type='vendor', entity_id=vendor_obj.id,
                    created_by=creator_name, 
                    **address_data
                )
                
                for contact in contacts_data:
                    vendor_contact_person.objects.db_manager(active_db).create(
                        vendor_id=vendor_obj.id, created_by=creator_name, **contact)
                
                vendor_obj._state.db = active_db
                return vendor_obj
        finally:
            clear_current_db_name()
            
    def update(self, instance, validated_data):
            active_db = self.context['request'].user.tenant_db_name # Using the helper property we discussed
            connect_to_db(active_db)
            
            # Pop nested data
            address_data = validated_data.pop('address', None)
            contacts_data = validated_data.pop('contacts', None)
            
            # Update Vendor fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save(using=active_db)
            
            # Update Address
            if address_data:
                addr_obj, _ = address.objects.db_manager(active_db).get_or_create(
                    entity_type='vendor', entity_id=instance.id
                )
                for attr, value in address_data.items():
                    setattr(addr_obj, attr, value)
                addr_obj.save(using=active_db)
                
            # Update Contacts (Optional: replace existing contacts with new ones)
            if contacts_data is not None:
                vendor_contact_person.objects.db_manager(active_db).filter(vendor=instance).delete()
                for contact in contacts_data:
                    vendor_contact_person.objects.db_manager(active_db).create(vendor=instance, **contact)
                    
            return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Use the actual DB name from context if available, otherwise fallback
        active_db = self.context['request'].user.db_name.strip().replace(" ", "_")
        connect_to_db(active_db)
        
        try:
            addr_obj = address.objects.db_manager(active_db).get(entity_type='vendor', entity_id=instance.id)
            ret['address'] = AddressSerializer(addr_obj).data
        except address.DoesNotExist:
            ret['address'] = None

        contacts_qs = vendor_contact_person.objects.db_manager(active_db).filter(vendor=instance)
        ret['contacts'] = ContactPersonSerializer(contacts_qs, many=True).data
        return ret
    
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeePermission
        fields = ['module_name', 'can_view', 'can_create', 'can_edit', 'can_status']

class EmployeeSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    address = AddressSerializer(required=False) # Use the existing serializer

    class Meta:
        model = Employee
        fields = '__all__'
        
    def get_permissions(self, obj):
        active_db = self.context['request'].user.db_name.strip().replace(" ", "_")

        perms = EmployeePermission.objects.using(active_db).filter(
            employee_id=obj.id
        )

        return PermissionSerializer(perms, many=True).data

    def create(self, validated_data):
        request = self.context.get('request')
        active_db = self.context['request'].user.db_name.strip().replace(" ", "_")
        connect_to_db(active_db)
        creator_name = getattr(request.user, 'employee_name', 'System')
        # Pop nested data
        permissions_data = validated_data.pop('permissions', [])
        address_data = validated_data.pop('address', None)
        password = validated_data.pop('password', 'defaultpassword') 
        
        with transaction.atomic(using=active_db):
            # 1. Create Employee in Tenant DB
            employee = Employee.objects.using(active_db).create(password=password, 
                                                                created_by=creator_name, **validated_data)
            
            # 2. Save Permissions: Use employee_id to bypass Database Router
            for perm in permissions_data:
                EmployeePermission.objects.using(active_db).create(employee_id=employee.id,
                                                                   created_by=creator_name, **perm)
            
            # 3. Save Address
            if address_data:
                address.objects.using(active_db).create(
                    entity_type='employee', entity_id=employee.id,created_by=creator_name,  **address_data
                )

        # 4. Save to Master DB (Auth)
        with transaction.atomic(using='default'):
            if not register_employee.objects.using('default').filter(mobile_number=validated_data['contact_number']).exists():
                register_employee.objects.using('default').create(
                    mobile_number=validated_data['contact_number'],
                    employee_name=validated_data['name'],
                    company_name=validated_data.get('department', 'N/A'), 
                    db_name=active_db,
                    role=validated_data['role'],
                    password=password 
                )
        return employee

    def update(self, instance, validated_data):
        active_db = self.context['request'].user.db_name.strip().replace(" ", "_")
        connect_to_db(active_db)
        
        permissions_data = validated_data.pop('permissions', None)
        address_data = validated_data.pop('address', None)
        
        # Update Employee fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=active_db)


        if permissions_data is not None:
            EmployeePermission.objects.using(active_db).filter(employee_id=instance.id).delete()
            for perm in permissions_data:
                EmployeePermission.objects.using(active_db).create(employee_id=instance.id, **perm)
                
        # Update Address
        if address_data:
            addr_obj, _ = address.objects.db_manager(active_db).get_or_create(
                entity_type='employee', entity_id=instance.id
            )
            for attr, value in address_data.items():
                setattr(addr_obj, attr, value)
            addr_obj.save(using=active_db)
                
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        active_db = self.context['request'].user.db_name.strip().replace(" ", "_")
        connect_to_db(active_db)
        
        # Fetch Address
        try:
            addr_obj = address.objects.db_manager(active_db).get(entity_type='employee', entity_id=instance.id)
            ret['address'] = AddressSerializer(addr_obj).data
        except address.DoesNotExist:
            ret['address'] = None

        # Fetch Permissions

        
        return ret