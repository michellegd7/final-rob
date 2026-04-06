from django.db import models


class Guard(models.Model):
    first_name   = models.CharField(max_length=50)
    last_name    = models.CharField(max_length=50)
    username     = models.CharField(max_length=50, default='')
    password     = models.CharField(max_length=50, default='')
    phone_number = models.CharField(max_length=15, blank=True, default='')
    address      = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Owner(models.Model):
    first_name   = models.CharField(max_length=50)
    last_name    = models.CharField(max_length=50)
    username     = models.CharField(max_length=50, unique=True)
    password     = models.CharField(max_length=128)
    phone_number = models.CharField(max_length=15, blank=True, default='')
    address      = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Vehicle(models.Model):
    owner        = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='vehicles', null=True, blank=True)
    plate_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20)

    def __str__(self):
        return self.plate_number


class Slot(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied',  'Occupied'),
    ]
    slot_number = models.CharField(max_length=10)
    slot_type   = models.CharField(max_length=20)
    slot_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    def __str__(self):
        return f"{self.slot_number} ({self.slot_type})"


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    vehicle    = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    slot       = models.ForeignKey(Slot, on_delete=models.CASCADE)
    guard      = models.ForeignKey(Guard, on_delete=models.SET_NULL, null=True, blank=True)
    owner      = models.ForeignKey(Owner, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    entry_time = models.DateTimeField()
    exit_time  = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"TKT-{str(self.id).zfill(4)}"


class Payment(models.Model):
    ticket         = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True, blank=True)
    amount         = models.DecimalField(max_digits=8, decimal_places=2)
    payment_date   = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20)
    payment_ref    = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return f"Payment {self.id}"