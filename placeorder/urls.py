from django.urls import path
from . import views



urlpatterns = [


    path('placeorder/',views.place_order,name='placeorder'),
    path('order/confirmation/<str:order_id>/', views.order_confirmation, name='order_confirmation'),

    path('order-details/<str:order_id>/', views.order_details, name='order_details'),     
    path('generate-invoice/<str:order_id>/', views.generate_invoice, name='generate_invoice'),
    path('cancel_product/<int:item_id>/', views.cancel_product, name='cancel_product'),
    path('return-product/<int:item_id>/', views.return_product, name='return_product'),
    


]
  