from django.db import models
from django.utils import timezone

class MpesaPayment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    # Core transaction fields
    checkout_request_id = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=20)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # M-Pesa response fields
    merchant_request_id = models.CharField(max_length=50, blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True)
    result_code = models.IntegerField(blank=True, null=True)
    result_description = models.TextField(blank=True, null=True)
    callback_metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    callback_received_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'M-Pesa Payment'
        verbose_name_plural = 'M-Pesa Payments'

    def __str__(self):
        return f"{self.checkout_request_id} - {self.phone_number} - KES {self.amount}"

    def mark_as_successful(self, receipt_number, callback_data):
        self.status = 'success'
        self.mpesa_receipt_number = receipt_number
        self.update_from_callback(callback_data)

    def mark_as_failed(self, callback_data):
        self.status = 'failed'
        self.update_from_callback(callback_data)

    def mark_as_cancelled(self, callback_data):
        self.status = 'cancelled'
        self.update_from_callback(callback_data)

    def update_from_callback(self, callback_data):
        self.callback_received_at = timezone.now()
        self.result_code = callback_data.get('ResultCode')
        self.result_description = callback_data.get('ResultDesc')
        self.callback_metadata = callback_data.get('CallbackMetadata', {})
        self.save()