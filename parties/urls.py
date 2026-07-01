# parties/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, ContactPersonViewSet

router = DefaultRouter()
# IMPORTANT: The router automatically adds 'customers/' 
# So the final URL becomes /api/customers/
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'contact-persons', ContactPersonViewSet, basename='contactperson')

urlpatterns = [
    path('', include(router.urls)), # No 'api/' here, it's already in mysite/urls.py
]