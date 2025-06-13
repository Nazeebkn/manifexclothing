from django.urls import path
from . import views


urlpatterns = [

    path('coupon/',views.coupon,name='coupon'),
    path('add_coupon/', views.add_coupon, name='add_coupon'),
    path('coupon/edit/<uuid:id>/', views.edit_coupon, name='edit_coupon'),
    path('coupon/delete/<uuid:id>/', views.delete_coupon, name='delete_coupon'),
    path('available_coupons/', views.available_coupons, name='available_coupons'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),



]