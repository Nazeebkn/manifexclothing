"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('admin/', admin.site.urls),
    path('',include('app1.urls')),
    path('accounts/', include('allauth.urls')),
    path('admin_panel/', include('admin_panel.urls')),
    path('', include('user.urls')),
    path('', include('categories.urls')),
    path('',include('products.urls')),
    path('',include('user_profile.urls')),
    path('',include('cart.urls')),
    path('', include('checkout.urls')),
    path('user/', include('user_profile.urls')),
    path('',include('placeorder.urls')),
    path('',include('order_management.urls')),
    path('',include('wishlist.urls')),
    path('',include('wallet.urls')),
    path('coupon/',include('coupon.urls')),
    path('',include('offer.urls')),
    path('',include('payment.urls')),
    path('',include('dashboard.urls')),
    path('',include('contact.urls')),



]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    