from .import views 
from django.urls import path


urlpatterns = [

    path('wishlist.html/',views.wishlist,name='wishlist'),
    path('add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove/<int:wishlist_item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),



]