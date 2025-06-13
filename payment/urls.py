from django.urls import path
from . import views

urlpatterns = [

    path('payment/', views.payment, name='payment'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('success/<str:order_id>/', views.order_confirmation, name='order_success'),
    path('order-failure/', views.order_failure, name='order_failure'),

]