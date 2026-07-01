from django.db import models

class customer(models.Model):
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive')]
    customer_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    gst_no = models.CharField(max_length=20, blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    
    class Meta:
        db_table = 'parties_customer'

    def __str__(self):
        return self.name

class contact_person(models.Model):
    customer = models.ForeignKey(customer, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=50)
    role = models.CharField(max_length=50)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    
    class Meta:
        db_table = 'parties_contact_person'

class address(models.Model):
    
    entity_type = models.CharField(max_length=50)
    entity_id = models.PositiveIntegerField()     
    
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    
    class Meta:
        db_table = 'parties_address'
        
class vendor(models.Model):
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive')]
    vendor_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    gst_no = models.CharField(max_length=20, blank=True)
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    
    class Meta:
        db_table = 'parties_vendor'

    def __str__(self):
        return self.name

class vendor_contact_person(models.Model):
    vendor = models.ForeignKey(vendor, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=50)
    role = models.CharField(max_length=50)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    
    class Meta:
        db_table = 'parties_vendor_contact_person'