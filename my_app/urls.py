from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('stk-push/', views.stk_push, name='stk_push'),
    path('callback/', views.stk_push_callback, name='stk_push_callback'),
    path('check-status/', views.check_status, name='check_status'),
]
