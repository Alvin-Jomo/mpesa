from django.contrib import admin
from .models import MpesaPayment

@admin.register(MpesaPayment)
class MpesaPaymentAdmin(admin.ModelAdmin):
    list_display = ('checkout_request_id', 'phone_number', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('phone_number', 'checkout_request_id', 'mpesa_receipt_number')
    readonly_fields = ('created_at', 'updated_at', 'callback_received_at')
    date_hierarchy = 'created_at'