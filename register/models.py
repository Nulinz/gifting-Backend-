from django.db import models


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

    def __str__(self):
        return self.company_name