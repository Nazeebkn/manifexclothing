from django.urls import path
from . import views

urlpatterns = [
    path('offer_list/', views.offer_list, name='offer_list'),
    path('add/', views.add_offer, name='add_offer'),
    path('edit/product/<int:offer_id>/', views.edit_product_offer, name='edit_product_offer'),
    path('edit/category/<int:offer_id>/', views.edit_category_offer, name='edit_category_offer'),
    path('delete/product/<int:offer_id>/', views.delete_product_offer, name='delete_product_offer'),
    path('delete/category/<int:offer_id>/', views.delete_category_offer, name='delete_category_offer'),
]