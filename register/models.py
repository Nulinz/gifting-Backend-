from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

# 1. Company Register Master Table
class company_register(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15)
    company_name = models.CharField(max_length=255)
    db_name = models.CharField(max_length=63, unique=True)
    gst_number = models.CharField(max_length=15)
    pan_number = models.CharField(max_length=10)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'company_register'

    def __str__(self):
        return self.company_name


class register_employee_manager(BaseUserManager):
    def create_user(self, mobile_number, employee_name, company_name, db_name, password=None):
        if not mobile_number:
            raise ValueError("Employees must have a valid mobile number to log in.")
        if not db_name:
            raise ValueError("Employees must be mapped to a valid db_name")
        
        user = self.model(
            mobile_number=mobile_number,
            employee_name=employee_name,
            company_name=company_name,
            db_name=db_name
        )
        user.set_password(password)
        user.save(using='default')  
        return user

    def create_superuser(self, mobile_number, employee_name, company_name, db_name, password=None):
        user = self.create_user(mobile_number, employee_name, company_name, db_name, password)
        user.save(using='default')
        return user


class register_employee(AbstractBaseUser):
    mobile_number = models.CharField(max_length=15, unique=True) 
    employee_name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    db_name = models.CharField(max_length=63)
    role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    # Set login field to mobile_number
    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = ['employee_name', 'company_name', 'db_name']

    objects = register_employee_manager()
    
    class Meta:
        db_table = 'register_employee'

    def __str__(self):
        return f"{self.employee_name} ({self.mobile_number})"