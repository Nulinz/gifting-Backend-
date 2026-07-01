"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from knox import views as knox_views

# Import views directly from your register app
from register.views import CompanyRegistrationView, TenantLoginView
from parties.views import CustomerViewSet, ContactPersonViewSet , VendorViewSet

# 1. Initialize the global DRF DefaultRouter
router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'contact-persons', ContactPersonViewSet, basename='contactperson')
router.register(r'vendors', VendorViewSet, basename='vendor')

# (When you build your business_app/parties views later, you will register them here)
# Example: router.register(r'customers', CustomerViewSet, basename='customer')

# 2. Main URL Configuration
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Unified API prefix handling both routers and direct paths
    path('api/', include([
        # Router endpoints (e.g., /api/customers/)
        path('', include(router.urls)),
        
        # Authentication & Tenant Registration Endpoints
        path('company-register/', CompanyRegistrationView.as_view(), name='company-register'),
        path('login/', TenantLoginView.as_view(), name='tenant-login'),
        path('logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    ])),
]
