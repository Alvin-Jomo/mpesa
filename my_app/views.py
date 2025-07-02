import json
import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django_daraja.mpesa.core import MpesaClient
from django.core.cache import cache
from django.conf import settings

# Logger setup
logger = logging.getLogger(__name__)

def index(request):
    """Render the main payment page"""
    return render(request, 'mpesa_payment.html')


@csrf_exempt
@require_POST
def stk_push(request):
    """Initiates M-Pesa STK push to user's phone"""
    try:
        cl = MpesaClient()

        # Extract form data
        phone = request.POST.get('phone', '').strip()
        amount = request.POST.get('amount', '').strip()
        reference = request.POST.get('reference', 'Payment').strip()[:20]

        # Basic validation
        if not phone or not amount:
            return JsonResponse({'status': 'error', 'message': 'Phone number and amount are required'}, status=400)

        # Validate amount
        try:
            amount = int(amount)
            if amount < 1:
                raise ValueError()
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Amount must be a number greater than 0'}, status=400)

        # Validate phone number
        if not (phone.startswith('254') and len(phone) == 12 and phone.isdigit()):
            return JsonResponse({'status': 'error', 'message': 'Phone number must be in format 254XXXXXXXXX'}, status=400)

        # Initiate STK push
        response = cl.stk_push(
            phone_number=phone,
            amount=amount,
            account_reference=reference,
            transaction_desc='Customer Payment',
            callback_url=settings.MPESA_CALLBACK_URL
        )

        # STK push was successful
        if response.response_code == '0':
            checkout_id = response.checkout_request_id
            # Store payment temporarily
            cache.set(checkout_id, {
                'status': 'pending',
                'phone': phone,
                'amount': amount,
                'reference': reference
            }, timeout=300)

            return JsonResponse({
                'status': 'success',
                'checkout_request_id': checkout_id,
                'customer_message': response.customer_message
            })

        # STK push failed
        return JsonResponse({
            'status': 'error',
            'message': response.error_message or 'Payment request failed'
        }, status=400)

    except Exception as e:
        logger.exception("STK Push Exception:")
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred during processing. Please try again.'
        }, status=500)


@csrf_exempt
@require_POST
def stk_push_callback(request):
    """Handles callback from M-Pesa API after payment attempt"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        callback = data.get('Body', {}).get('stkCallback', {})
        checkout_id = callback.get('CheckoutRequestID')
        result_code = callback.get('ResultCode')
        result_desc = callback.get('ResultDesc', 'Payment failed')

        if checkout_id:
            # Determine payment outcome
            if result_code == 0:
                status = {'status': 'success', 'message': 'Payment completed successfully'}
            elif result_code == 1032:
                status = {'status': 'cancelled', 'message': 'Transaction was cancelled by the user'}
            else:
                status = {'status': 'failed', 'message': result_desc}

            # Update cache with final status
            cache.set(checkout_id, status, timeout=300)

        return HttpResponse(status=200)

    except json.JSONDecodeError:
        logger.error("Invalid JSON received in callback.")
        return HttpResponse(status=400)
    except Exception as e:
        logger.exception("Callback processing error:")
        return HttpResponse(status=400)


@csrf_exempt
@require_GET
def check_status(request):
    """Returns the status of a previously initiated STK push request"""
    checkout_id = request.GET.get('checkout_request_id')

    if not checkout_id:
        return JsonResponse({
            'status': 'error',
            'message': 'Checkout Request ID is required'
        }, status=400)

    # Fetch status from cache
    status_data = cache.get(checkout_id, {'status': 'pending'})

    # Clean up cache if final state reached
    if status_data.get('status') in ['success', 'cancelled', 'failed']:
        cache.delete(checkout_id)

    return JsonResponse(status_data)
