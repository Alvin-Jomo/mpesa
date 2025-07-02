from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('daraja/stk-push', views.stk_push_callback, name='mpesa_stk_push_callback'),
    path('stk-push/', views.stk_push, name='stk_push'),
    path('callback', views.stk_push_callback, name='stk_push_callback'),
    path('check_status', views.check_status, name='check_status'),
    
]

# Note: Ensure that the paths in your views match the actual view functions defined in your views.py file.
# This file defines the URL patterns for your Django application, mapping URLs to their respective view functions
# and allowing you to handle requests for different endpoints in your application.
# The `include` function is used to include URLs from other applications, such as the Django Daraja app for handling M-Pesa payments.
# The `path` function is used to define the URL patterns, where the first argument is the URL path,
# the second argument is the view function that will handle requests to that path,
# and the `name` argument is an optional name for the URL pattern that can be used for reverse URL resolution.
# The `urlpatterns` list is the main entry point for URL routing in your Django application.
# It allows you to define how different URLs should be handled by your application.
# The `views` module is imported to access the view functions defined in your application.
# The `urlpatterns` list is then populated with the URL patterns,
# which map specific URL paths to their corresponding view functions.
# This allows Django to route incoming requests to the appropriate view based on the requested URL.