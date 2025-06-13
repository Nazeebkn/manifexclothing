from django.urls import path
from . import views

urlpatterns=[

  path('products/',views.product_list,name='product_list'),
  path('products/add',views.add_product,name='add_product'),
  path('products/<int:product_id>/manage-variants/', views.add_variant, name='manage_variants'),
  path('products/edit/<int:product_id>',views.edit_product,name='edit_product'),
  path('products/<int:product_id>/toggle-status/',views.toggle_product_status,name='toggle_product_status'),
  path('products/details/<int:variant_id>/', views.product_details, name='product_details'),
  path('shop/',views.shop,name='shop'),
  path('products/<int:product_id>/variants/', views.variant_list, name='variant_list'),
  path('products/<int:product_id>/variants/add/', views.add_variant, name='add_variant'),
  path('products/<int:product_id>/variants/<int:variant_id>/edit/', views.edit_variant, name='edit_variant'),
  path('products/<int:product_id>/variants/<int:variant_id>/delete/', views.delete_variant, name='delete_variant'),

  path('products/variants/<int:variant_id>/size/', views.add_size, name='add_size'),

  
 

]