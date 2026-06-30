from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    mobile_number = models.CharField(max_length=15, unique=True)

    USERNAME_FIELD = 'username' 
    REQUIRED_FIELDS = ['mobile_number', 'email']

class CompanyRegistry(models.Model):
    # Basic Info
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=15)
    
    # Business Info
    company_name = models.CharField(max_length=100)
    db_name = models.CharField(max_length=50, unique=True) # Will store 'db_companyname'
    gst_number = models.CharField(max_length=20)
    pan_number = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    password = models.CharField(max_length=128)

    def __str__(self):
        return self.company_name
    
class Employee(models.Model):
    e_code = models.CharField(max_length=50)
    e_name = models.CharField(max_length=100)
    e_gender = models.CharField(max_length=10)
    e_department = models.CharField(max_length=50)
    e_role = models.CharField(max_length=50)
    e_number = models.IntegerField()
    e_mail = models.EmailField()
    password = models.CharField(max_length=100)
    image = models.FileField(upload_to='employees/')
    remarks = models.TextField()
    status = models.CharField(max_length=20)
    created_by = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.e_name
    
    class Meta:
        managed = False

class EmployeePermission(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    module_name = models.CharField(max_length=50)
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_status_tog = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.employee.e_name} - {self.module_name}"
    
    class Meta:
        managed = False