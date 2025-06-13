from django.urls import path
from . import views


urlpatterns = [
  
    path('checkout/', views.checkout, name='checkout'),
    
    path('order-success/<str:order_id>/', views.order_success, name='order_success'),
    path('checkout_add_address/',views.checkout_add_address,name='checkout_add_address'),
    path('checkout_edit_address/<int:address_id>/',views.checkout_edit_address,name='checkout_edit_address'),
    
]