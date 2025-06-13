from .import views 
from django.urls import path


urlpatterns = [

path('user_profile/',views.user_profile,name='user_profile'),
path('edit_profile/',views.edit_profile,name='edit_profile'),
path('profile_otp_verify/',views.profile_otp,name='profile_otp_verify'),
path('new_mail/', views.new_email, name='new_mail'),
path('newmail_otp_verify/',views.newmail_otp_verify,name='newmail_otp_verify'),
path('my_profile/',views.my_profile,name='my_profile'),
path('change_password/',views.change_password,name='change_password'),
path('address/',views.address,name='address'),
path('add_address/',views.add_address,name='add_address'),
path('edit_address/<int:address_id>/', views.edit_address, name='edit_address'),
path('delete_address/<int:address_id>/', views.delete_address, name='delete_address'),
path('set_default_address/<int:address_id>/', views.set_default_address, name='set_default_address'),
path('my_orders/', views.my_orders, name='my_orders'),
path('referrals/', views.referrals, name='referrals'),






]