import json
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
            
            account_reference = request.POST.get('reference', 'Payment')[:20]  # Limit to 20 chars
            transaction_desc = 'Customer Payment'
            callback_url = 'https://mpesa-ifvv.onrender.com/callback'  # Update with your actual callback URL
            
            response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)
            
            if response.response_code == "0":
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
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@csrf_exempt
def stk_push_callback(request):
    if request.method == 'POST':
        try:
            # Safely parse JSON data
            try:
                data = json.loads(request.body.decode('utf-8'))
            except json.JSONDecodeError:
                return HttpResponse(status=400, content="Invalid JSON")
                
            callback_data = data.get('Body', {}).get('stkCallback', {})
            result_code = callback_data.get('ResultCode')
            result_desc = callback_data.get('ResultDesc', 'Payment failed')
            
            # Store the result in session
            if result_code == '0':
                request.session['mpesa_status'] = 'success'
                request.session['mpesa_message'] = 'Payment completed successfully'
            elif result_code == '1032':
                request.session['mpesa_status'] = 'cancelled'
                request.session['mpesa_message'] = 'Transaction was cancelled by the user'
            else:
                request.session['mpesa_status'] = 'failed'
                request.session['mpesa_message'] = result_desc
            
            return HttpResponse(status=200, content="Callback received successfully")
        except Exception as e:
            return HttpResponse(status=400, content=f"Error processing callback: {str(e)}")
    return HttpResponse(status=405, content="Method not allowed")

@csrf_exempt
def check_status(request):
    if request.method == 'GET':
        status = request.session.get('mpesa_status')
        message = request.session.get('mpesa_message', '')
        
        response_data = {'status': status, 'message': message}
        
        # Clear the session only if we found a status
        if status:
            try:
                del request.session['mpesa_status']
                del request.session['mpesa_message']
            except KeyError:
                pass
                
        return JsonResponse(response_data)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)