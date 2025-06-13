from .import views 
from django.urls import path


urlpatterns = [

        path('wallet/',views.wallet,name='wallet'),
        path('wallet_management/', views.wallet_management, name='wallet_management'),
        path('wallet_transaction_detail/<str:transaction_id>/', views.wallet_transaction_detail, name='wallet_transaction_detail'),




]