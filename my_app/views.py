from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_daraja.mpesa.core import MpesaClient

def index(request):
    return render(request, 'mpesa_payment.html')

@csrf_exempt
def stk_push(request):
    if request.method == 'POST':
        try:
            cl = MpesaClient()
            phone_number = request.POST.get('phone')
            amount = request.POST.get('amount')
            
            # Validate required fields
            if not phone_number or not amount:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Phone number and amount are required'
                }, status=400)
            
            try:
                amount = int(amount)
            except (ValueError, TypeError):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Amount must be a valid number'
                }, status=400)
            
            account_reference = request.POST.get('reference', 'Payment')
            transaction_desc = 'Customer Payment'
            callback_url = 'https://yourdomain.com/stk-callback'  # Update with your callback URL
            
            response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)
            
            if response.response_code == "0":
                return JsonResponse({
                    'status': 'success',
                    'CustomerMessage': response.customer_message
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
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

def stk_push_callback(request):
    data = request.body
    # Process the callback data here
    return HttpResponse("STK Push Callback Received")