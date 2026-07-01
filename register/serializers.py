import re
from rest_framework import serializers
from .models import company_register, register_employee

class CompanyRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    db_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = company_register
        fields = [
            'full_name', 'email', 'mobile_number', 'company_name', 
             'db_name','gst_number', 'pan_number', 'address', 
            'city', 'state', 'pincode', 'password'
        ]
     

    def validate(self, attrs):
        company_name = attrs.get('company_name', '')

        if not company_name:
            raise serializers.ValidationError({"company_name": "Company name is required."})

        # Convert to lowercase and replace spaces/hyphens with underscores
        clean_name = company_name.strip().lower()
        clean_name = re.sub(r'[\s\-]+', '_', clean_name)
        
        # Strip out any remaining non-alphanumeric or non-underscore characters
        clean_name = re.sub(r'[^a-z0-9_]', '', clean_name)
        
        # Generate the final physical database name string
        generated_db_name = f"{clean_name}_db"

        # Check for database naming duplicate collisions in your master registry
        if company_register.objects.filter(db_name=generated_db_name).exists():
            raise serializers.ValidationError({
                "company_name": "A database generated from this company name already exists."
            })

        # Inject the generated name into the validation stream for views.py
        attrs['db_name'] = generated_db_name
        return attrs

class RegisterEmployeeSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    class Meta:
        model =register_employee
        fields = ['id', 'mobile_number', 'employee_name', 'company_name', 'db_name', 'password']