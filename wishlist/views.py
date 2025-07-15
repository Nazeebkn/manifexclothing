from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wishlist
from products.models import Product, ProductVariant, Size  # Import from products app
from cart.models import Cart, CartItem  # Import from cart app

@login_required
def wishlist(request):
    # Fetch wishlist items with related data to reduce queries
    wishlist_items = Wishlist.objects.filter(
        user=request.user,
        variant__product__is_active=True
    )


    if request.method == 'POST':
        action = request.POST.get('action')
        wishlist_item_id = request.POST.get('wishlist_item_id')
        print(wishlist_item_id)

        if not wishlist_item_id:
            messages.error(request, "Invalid wishlist item.")
            return redirect('wishlist')

        wishlist_item = get_object_or_404(
            Wishlist,
            id=wishlist_item_id,
            user=request.user
        )

        if action == 'add_to_cart':
            variant = wishlist_item.variant
            size = wishlist_item.size

            if not variant or not size:
                messages.error(request, "Variant or size not specified for this wishlist item.")
                return redirect('wishlist')

            # Check stock with edge case handling
            if not size.stock or size.stock <= 0:
                messages.error(request, f"Size {size.size} is out of stock for {variant.product.name} ({variant.color}).")
                return redirect('wishlist')

            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant=variant,
                size=size
            )
            if not created:
                if size.stock >= cart_item.quantity + 1:
                    cart_item.quantity += 1
                    cart_item.save()
                else:
                    messages.error(request, f"Insufficient stock for {variant.product.name} in size {size.size}.")
                    return redirect('wishlist')

            wishlist_item.delete()
            messages.success(request, f"{variant.product.name} moved to your cart.")
            return redirect('cart')

    # wishlist_count = wishlist_items.count()

    context = {
        'wishlist_items': wishlist_items,
        # 'wishlist_count': wishlist_count,
    }
    return render(request, 'wishlist.html', context)



@login_required
def remove_from_wishlist(request, wishlist_item_id):
    print("the method is being called")
    wishlist_item = get_object_or_404(
        Wishlist,
        id=wishlist_item_id,
        user=request.user
    )

    if request.method == 'POST':
        print("the method is post")
        wishlist_item.delete()
        messages.success(request, f"{wishlist_item.variant.product.name} removed from your wishlist.")
        return redirect('wishlist')

    return redirect('wishlist')








@login_required(login_url='login')
def add_to_wishlist(request,product_id):

    if request.method == 'POST':
        print(product_id)
        size_id = request.POST.get("size_id")
        print(size_id)

        variant = get_object_or_404(ProductVariant, id=product_id)
        print(variant)

        size = get_object_or_404(Size, id=size_id)

       
        if not size.stock or size.stock <= 0:
            messages.error(request, f"Size {size.size} is out of stock for  ({variant.color}).")
            return redirect('product_details', variant_id=variant.id)

        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            variant=variant,
            size=size
        )
        if created:
            messages.success(request, f"{variant.product.name} ({variant.color}) added to your wishlist.")
        else:
            messages.info(request, f"{variant.product.name} ({variant.color}) is already in your wishlist.")
        
        return redirect('wishlist')
    
    return redirect('product_details', variant_id=product_id)


