from rest_framework import serializers
from .models import customer, contact_person, address
from mysite.tenant_context import get_current_db_name
from django.conf import settings
from django.db import connections
from mysite.tenant_context import get_current_db_name ,set_current_db_name, clear_current_db_name


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = address
        exclude = ['entity_type', 'entity_id']


class ContactPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = contact_person
        fields = ['id', 'name', 'department', 'role', 'email', 'mobile']


class CustomerSerializer(serializers.ModelSerializer):
    address = AddressSerializer(write_only=True)
    contacts = ContactPersonSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = customer
        fields = ['id', 'customer_code', 'name', 'email', 'mobile', 'gst_no', 'remarks', 'status', 'address', 'contacts']
        # Disables automatic boot-time model-level default validation lookups
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

        
        
        # 1. Look up the user's tenant database just like above
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
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_db = getattr(request.user, 'db_name', None)
            if user_db:
                active_db = user_db.strip().replace(" ", "_")

        set_current_db_name(active_db)

        try:
            address_data = validated_data.pop('address')
            contacts_data = validated_data.pop('contacts', [])
            
            customer_obj = customer.objects.db_manager(active_db).create(**validated_data)

            address.objects.db_manager(active_db).create(
                entity_type='customer', 
                entity_id=customer_obj.id, 
                **address_data
            )
            
            for contact in contacts_data:
                contact_person.objects.db_manager(active_db).create(customer=customer_obj, **contact)
                
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
        contacts_qs = contact_person.objects.db_manager(active_db).filter(customer=instance)
        ret['contacts'] = ContactPersonSerializer(contacts_qs, many=True).data

        return ret