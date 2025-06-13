from django.urls import path
from . import views

urlpatterns = [
    
  path('users/',views.user_management,name='user_management'),
path('dashboard/block_user/<int:user_id>/', views.block_user, name='block_user'),
path('dashboard/unblock_user/<int:user_id>/', views.unblock_user, name='unblock_user'),
    
]