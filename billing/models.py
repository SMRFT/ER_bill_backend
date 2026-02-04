from django.db import models



class ERBilling(models.Model):
    uhid = models.CharField(max_length=50)
    patientname = models.CharField(max_length=150)
    age = models.CharField(max_length=20,blank=True, null=True)
    gender = models.CharField(max_length=20,blank=True, null=True)
    phonenumber = models.CharField(max_length=20,blank=True, null=True)
    billnumber = models.CharField(primary_key=True,max_length=50)
    doctorname = models.CharField(max_length=150,blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    payment_mode = models.JSONField(null=True, blank=True)

    # ONLY PROCEDURES STORED AS JSON
    procedures = models.JSONField() 

    # DISCOUNT FIELDS (NOT JSON)
    discount_type = models.CharField(max_length=10,blank=True, null=True)   # "%" or "amount"
    discount_value = models.FloatField(max_length=10,blank=True, null=True)              # 5 or 500
    discount_amount = models.FloatField(max_length=10,blank=True, null=True)             # calculated amount

    total = models.FloatField()
    net_amount = models.FloatField(max_length=10,blank=True, null=True)
    shiftno = models.CharField(max_length=20, unique=True)  # 2526/000001
    created_by = models.CharField(max_length=100, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    pharmacist_id = models.CharField(max_length=20, null=True, blank=True)
    lastmodified_by = models.CharField(max_length=100, blank=True, null=True)
    lastmodified_date = models.DateTimeField(auto_now_add=True)
    billing_status = models.CharField(max_length=10,default="Billed")
    def __str__(self):
        return f"{self.patientname} - {self.billnumber}"



class Shiftdetails(models.Model):
    starttime = models.DateTimeField(null=True, blank=True)
    endtime = models.DateTimeField(null=True, blank=True)
    shiftno = models.CharField(max_length=20, unique=True)  # 2526/000001
    is_active = models.BooleanField(default=False)

    created_by = models.CharField(max_length=100, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
