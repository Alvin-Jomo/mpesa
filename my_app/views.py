import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django_daraja.mpesa.core import MpesaClient
from django.core.cache import cache
from django.conf import settings
from django.shortcuts import render

logger = logging.getLogger(__name__)

def index(request):
    """
    Render the main page with the payment form.
    """
    return render(request, 'mpesa_payment.html')

@csrf_exempt
@require_POST
def stk_push(request):
    try:
        cl = MpesaClient()
        phone_number = request.POST.get('phone', '').strip()
        amount = request.POST.get('amount', '').strip()
        
        # Validate inputs
        if not (phone_number and amount):
            return JsonResponse({
                'status': 'error',
                'message': 'Phone number and amount are required'
            }, status=400)
        
        try:
            amount = int(amount)
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
        
        # Process payment
        response = cl.stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=request.POST.get('reference', 'Payment')[:20],
            transaction_desc='Customer Payment',
            callback_url=settings.MPESA_CALLBACK_URL
        )
        
        if response.response_code == "0":
            # Store in cache for status checking
            cache.set(response.checkout_request_id, {
                'status': 'pending',
                'phone': phone_number,
                'amount': amount
            }, timeout=300)
            
            return JsonResponse({
                'status': 'success',
                'checkout_request_id': response.checkout_request_id,
                'customer_message': response.customer_message
            })
        
        return JsonResponse({
            'status': 'error',
            'message': response.error_message or 'Payment request failed'
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
    try:
        data = json.loads(request.body.decode('utf-8'))
        logger.info(f"Raw callback received: {data}")
        
        callback = data.get('Body', {}).get('stkCallback', {})
        checkout_id = callback.get('CheckoutRequestID')
        result_code = callback.get('ResultCode')
        
        if not checkout_id:
            return HttpResponse(status=400)
        
        # Process different statuses
        if result_code == 0:  # Success
            items = callback.get('CallbackMetadata', {}).get('Item', [])
            receipt = next((i['Value'] for i in items if i.get('Name') == 'MpesaReceiptNumber'), None)
            
            cache.set(checkout_id, {
                'status': 'success',
                'message': 'Payment completed',
                'receipt': receipt,
                'code': result_code
            }, timeout=300)
            
        elif result_code == 1032:  # Cancelled
            cache.set(checkout_id, {
                'status': 'cancelled',
                'message': 'Transaction cancelled by user',
                'code': result_code
            }, timeout=300)
            
        else:  # Other errors
            cache.set(checkout_id, {
                'status': 'failed',
                'message': callback.get('ResultDesc', 'Payment failed'),
                'code': result_code
            }, timeout=300)
            
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Callback Error: {str(e)}", exc_info=True)
        return HttpResponse(status=400)

@csrf_exempt
@require_GET
def check_status(request):
    checkout_id = request.GET.get('checkout_request_id')
    if not checkout_id:
        return JsonResponse({
            'status': 'error',
            'message': 'Checkout ID required'
        }, status=400)
    
    status_data = cache.get(checkout_id, {'status': 'pending'})
    return JsonResponse(status_data)