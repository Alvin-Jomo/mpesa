
from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('my_app.urls')),
    path('daraja/', include('django_daraja.urls')),
]