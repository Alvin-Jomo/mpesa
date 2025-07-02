import json
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django_daraja.mpesa.core import MpesaClient
from django.core.cache import cache

def index(request):
    """
    Render the index page with a simple form for M-Pesa STK push.
    """
    return render(request, 'mpesa_payment.html')

@csrf_exempt
@require_POST
def stk_push(request):
    try:
        cl = MpesaClient()
        phone_number = request.POST.get('phone', '').strip()
        amount = request.POST.get('amount', '').strip()
        
        # Validate required fields
        if not phone_number or not amount:
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
                'message': 'Amount must be a valid number greater than 0'
            }, status=400)
        
        # Validate phone number format (254XXXXXXXXX)
        if not phone_number.startswith('254') or len(phone_number) != 12 or not phone_number[1:].isdigit():
            return JsonResponse({
                'status': 'error',
                'message': 'Phone number must be in format 254XXXXXXXXX'
            }, status=400)
        
        account_reference = request.POST.get('reference', 'Payment')[:20]
        transaction_desc = 'Customer Payment'
        callback_url = 'https://mpesa-ifvv.onrender.com/callback/'
        
        response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)
        
        if response.response_code == "0":
            # Store the checkout request ID in cache with a timeout
            cache.set(response.checkout_request_id, {
                'status': 'pending',
                'phone': phone_number,
                'amount': amount
            }, timeout=300)  # 5 minutes timeout
            return JsonResponse({
                'status': 'success',
                'CustomerMessage': response.customer_message,
                'CheckoutRequestID': response.checkout_request_id
            })
        return JsonResponse({
            'status': 'error',
            'message': response.error_message or 'Payment request failed'
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }, status=500)

@csrf_exempt
@require_POST
def stk_push_callback(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        callback_data = data.get('Body', {}).get('stkCallback', {})
        checkout_request_id = callback_data.get('CheckoutRequestID')
        result_code = callback_data.get('ResultCode')
        result_desc = callback_data.get('ResultDesc', 'Payment failed')
        
        if checkout_request_id:
            if result_code == '0':
                cache.set(checkout_request_id, {
                    'status': 'success',
                    'message': 'Payment completed successfully'
                }, timeout=300)
            elif result_code == '1032':
                cache.set(checkout_request_id, {
                    'status': 'cancelled',
                    'message': 'Transaction was cancelled by the user'
                }, timeout=300)
            else:
                cache.set(checkout_request_id, {
                    'status': 'failed',
                    'message': result_desc
                }, timeout=300)
        
        return HttpResponse(status=200)
    except Exception as e:
        return HttpResponse(status=400)

@csrf_exempt
@require_GET
def check_status(request):
    checkout_request_id = request.GET.get('checkout_request_id')
    if not checkout_request_id:
        return JsonResponse({
            'status': 'error',
            'message': 'Checkout Request ID is required'
        }, status=400)
    
    status_data = cache.get(checkout_request_id, {})
    return JsonResponse(status_data)        