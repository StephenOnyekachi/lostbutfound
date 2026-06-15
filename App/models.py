
from django.db import models
from django.contrib.auth.models import User #AbstractUser
from django.utils.text import slugify
import uuid
from datetime import timedelta
from django.utils import timezone

# Create your models here.

class Plan(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    name = models.CharField(max_length=50, default='Name')

    def __str__(self):
        return f"{self.name} - {self.amount}"
    

class Org(models.Model):

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    orgname = models.CharField(max_length=200)
    subdomain = models.CharField(max_length=100, unique=True)

    # =========================
    # SUBSCRIPTION SYSTEM (FIXED)
    # =========================

    trial_start = models.DateField(default=timezone.now)
    trial_end = models.DateField(blank=True, null=True)
    subscription_end = models.DateField(blank=True, null=True)
    is_trial = models.BooleanField(default=True)

    logo = models.ImageField(upload_to='picture', blank=True, null=True)
    date_joined = models.DateField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='owned_organizations'
    )

    owner_number = models.CharField(max_length=20, blank=True)

    plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        related_name='organizations_plan'
    )

    def save(self, *args, **kwargs):
        # FIRST TIME SETUP ONLY
        if not self.trial_start:
            self.trial_start = timezone.now().date()

        if not self.trial_end:
            self.trial_end = self.trial_start + timedelta(days=30)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.orgname
       

class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('member', 'Member'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    gender = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name='profiles')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['org']),
        ]


class Item(models.Model):
    CATEGORY_CHOICES = [
        ('phone', 'Phone'),
        ('wallet', 'Wallet'),
        ('id_card', 'ID Card'),
        ('laptop', 'Laptop'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('found', 'Found'),
        ('claimed', 'Claimed'),
        # ('returned', 'Returned'),
    ]

    name = models.CharField(max_length=200)
    picture = models.ImageField(upload_to='picture', blank=True, null=True)
    description = models.TextField(null=True, blank=True)
    location_found = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='found')
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name='items')
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='items_posted')
    date_posted = models.DateTimeField(auto_now_add=True)
    item_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        indexes = [
            models.Index(fields=['org']),
            models.Index(fields=['name']),
            models.Index(fields=['status']),
        ]


class Claim(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name='claims')
    proof = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    admin_note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.claimant.username} - {self.item.name}"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['item', 'claimant'],
                name='unique_claim_per_user_item'
            )
        ]


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]

    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='NGN')
    reference = models.CharField(max_length=100, unique=True)
    paystack_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reference} - {self.status}"

    class Meta:
        indexes = [
            models.Index(fields=['org']),
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
        ]



        