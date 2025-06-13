from django.urls import path
from . import  views
from placeorder.views import order_details

urlpatterns = [

    path('order_management/',views.order_management,name='order_management'),
    path('orders/<str:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('orders/<str:order_id>/detail/', views.order_management_details, name='order_management_details'),   
    path('order-details/<str:order_id>/', order_details, name='order_details'), 
    path('update-order-status/<str:order_id>/', views.update_order_status, name='update_order_status'),
    path('update-order-item-status/<int:item_id>/', views.update_order_item_status, name='update_order_item_status'),


    

]   