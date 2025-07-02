import json
import logging
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django_daraja.mpesa.core import MpesaClient
from django.core.cache import cache
from django.conf import settings

# Initialize logger
logger = logging.getLogger(__name__)

def index(request):
    """Render the M-Pesa payment page"""
    return render(request, 'mpesa_payment.html')

@csrf_exempt
@require_POST
def stk_push(request):
    """Handle STK push payment requests"""
    try:
        # Initialize M-Pesa client
        cl = MpesaClient()
        
        # Get and validate parameters
        phone_number = request.POST.get('phone', '').strip()
        amount = request.POST.get('amount', '').strip()
        account_reference = request.POST.get('reference', 'Payment')[:20]
        
        # Validate required fields
        if not all([phone_number, amount]):
            return JsonResponse({
                'status': 'error',
                'message': 'Phone number and amount are required'
            }, status=400)
        
        # Validate amount
        try:
            amount = int(amount)
            if amount < 1:
                raise ValueError("Amount must be at least 1")
        except (ValueError, TypeError):
            return JsonResponse({
                'status': 'error',
                'message': 'Amount must be a valid number greater than 0'
            }, status=400)
        
        # Validate phone number format (254XXXXXXXXX)
        if (not phone_number.startswith('254') or 
            len(phone_number) != 12 or 
            not phone_number[1:].isdigit()):
            return JsonResponse({
                'status': 'error',
                'message': 'Phone number must be in format 254XXXXXXXXX'
            }, status=400)
        
        # Process STK push
        response = cl.stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=account_reference,
            transaction_desc='Customer Payment',
            callback_url=settings.MPESA_CALLBACK_URL
        )
        
        # Handle response
        if response.response_code == "0":
            # Cache payment details
            cache.set(response.checkout_request_id, {
                'status': 'pending',
                'phone': phone_number,
                'amount': amount,
                'reference': account_reference
            }, timeout=300)  # 5 minutes
            
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
            'message': 'Payment processing failed. Please try again.'
        }, status=500)

@csrf_exempt
@require_POST
def stk_push_callback(request):
    """Handle M-Pesa callback notifications"""
    try:
        # Parse callback data
        data = json.loads(request.body.decode('utf-8'))
        callback = data.get('Body', {}).get('stkCallback', {})
        
        # Extract relevant information
        checkout_request_id = callback.get('CheckoutRequestID')
        result_code = callback.get('ResultCode')
        result_desc = callback.get('ResultDesc', 'Payment failed')
        
        if checkout_request_id:
            # Update payment status in cache
            status_update = {
                'status': 'failed',
                'message': result_desc
            }
            
            if result_code == '0':
                status_update = {
                    'status': 'success',
                    'message': 'Payment completed successfully'
                }
            elif result_code == '1032':
                status_update = {
                    'status': 'cancelled',
                    'message': 'Transaction was cancelled by the user'
                }
            
            cache.set(checkout_request_id, status_update, timeout=300)
        
        return HttpResponse(status=200)
    
    except json.JSONDecodeError:
        logger.error("Callback Error: Invalid JSON received")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Callback Error: {str(e)}", exc_info=True)
        return HttpResponse(status=400)

@csrf_exempt
@require_GET
def check_status(request):
    """Check payment status using checkout request ID"""
    checkout_request_id = request.GET.get('checkout_request_id')
    
    if not checkout_request_id:
        return JsonResponse({
            'status': 'error',
            'message': 'Checkout Request ID is required'
        }, status=400)
    
    # Get status from cache
    status_data = cache.get(checkout_request_id, {'status': 'pending'})
    
    # Clear cache if status is final
    if status_data.get('status') in ['success', 'cancelled', 'failed']:
        cache.delete(checkout_request_id)
    
    return JsonResponse(status_data)