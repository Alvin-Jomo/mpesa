import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django_daraja.mpesa.core import MpesaClient
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from .models import MpesaPayment
from django.utils import timezone

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'mpesa_payment.html')

@csrf_exempt
@require_POST
def stk_push(request):
    """Handle STK push payment requests"""
    try:
        cl = MpesaClient()
        phone_number = request.POST.get('phone', '').strip()
        amount = request.POST.get('amount', '').strip()
        reference = request.POST.get('reference', 'Payment')[:20]
        
        # Validate inputs
        if not (phone_number and amount):
            return JsonResponse({
                'status': 'error',
                'message': 'Phone number and amount are required'
            }, status=400)
        
        try:
            amount = float(amount)
            if amount < 1:
                raise ValueError("Amount must be at least 1")
        except (ValueError, TypeError):
            return JsonResponse({
                'status': 'error',
                'message': 'Amount must be a valid number ≥ 1'
            }, status=400)
        
        if not (phone_number.startswith('254') and len(phone_number) == 12 and phone_number[1:].isdigit()):
            return JsonResponse({
                'status': 'error',
                'message': 'Phone must be format 254XXXXXXXXX'
            }, status=400)
        
        # Initiate payment
        response = cl.stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=reference,
            transaction_desc='Customer Payment',
            callback_url=settings.MPESA_CALLBACK_URL
        )
        
        if response.response_code == "0":
            # Create payment record
            payment = MpesaPayment.objects.create(
                checkout_request_id=response.checkout_request_id,
                phone_number=phone_number,
                amount=amount,
                reference=reference,
                merchant_request_id=response.merchant_request_id,
                status='pending'
            )
            
            return JsonResponse({
                'status': 'success',
                'checkout_request_id': payment.checkout_request_id,
                'customer_message': response.customer_message,
                'timestamp': payment.created_at.isoformat()
            })
        
        return JsonResponse({
            'status': 'error',
            'message': response.error_message or 'Payment request failed',
            'response_code': response.response_code
        })
        
    except Exception as e:
        logger.error(f"STK Push Error: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Payment processing failed'
        }, status=500)

@csrf_exempt
@require_POST
def stk_push_callback(request):
    """Handle M-Pesa payment callbacks"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        logger.info(f"Callback received: {data}")
        
        callback = data.get('Body', {}).get('stkCallback', {})
        checkout_id = callback.get('CheckoutRequestID')
        result_code = callback.get('ResultCode')
        
        if not checkout_id:
            logger.error("Missing CheckoutRequestID in callback")
            return HttpResponse(status=400)
        
        # Get or create payment record
        payment = get_object_or_404(MpesaPayment, checkout_request_id=checkout_id)
        
        # Process different statuses
        if result_code == 0:  # Success
            items = callback.get('CallbackMetadata', {}).get('Item', [])
            receipt = next((i['Value'] for i in items if i.get('Name') == 'MpesaReceiptNumber'), None)
            payment.mark_as_successful(receipt, callback)
            
        elif result_code == 1032:  # Cancelled
            payment.mark_as_cancelled(callback)
            
        else:  # Other errors
            payment.mark_as_failed(callback)
            
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Callback Error: {str(e)}", exc_info=True)
        return HttpResponse(status=500)

@csrf_exempt
@require_GET
def check_status(request):
    """Check payment status using checkout request ID"""
    checkout_id = request.GET.get('checkout_request_id')
    
    if not checkout_id:
        return JsonResponse({
            'status': 'error',
            'message': 'Checkout Request ID is required'
        }, status=400)
    
    payment = get_object_or_404(MpesaPayment, checkout_request_id=checkout_id)
    
    response_data = {
        'status': payment.status,
        'phone': payment.phone_number,
        'amount': float(payment.amount),
        'reference': payment.reference,
        'created_at': payment.created_at.isoformat(),
        'updated_at': payment.updated_at.isoformat(),
    }
    
    if payment.status == 'success':
        response_data.update({
            'receipt': payment.mpesa_receipt_number,
            'message': 'Payment completed successfully'
        })
    elif payment.status == 'cancelled':
        response_data['message'] = 'Transaction cancelled by user'
    elif payment.status == 'failed':
        response_data['message'] = payment.result_description or 'Payment failed'
    
    return JsonResponse(response_data)