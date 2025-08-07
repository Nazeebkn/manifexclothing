from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wishlist
from products.models import Product, ProductVariant, Size  
from cart.models import Cart, CartItem 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(
        user=request.user,
        variant__product__is_active=True
    ).order_by('-id')

    items_per_page = 4
    paginator = Paginator(wishlist_items, items_per_page)
    page = request.GET.get('page')
    
    try:
        wishlist_items_paginated = paginator.page(page)
    except PageNotAnInteger:
        wishlist_items_paginated = paginator.page(1)
    except EmptyPage:
        wishlist_items_paginated = paginator.page(paginator.num_pages)


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


    context = {
        'wishlist_items': wishlist_items_paginated,
    }
    return render(request, 'wishlist.html', context)


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Wishlist

@login_required
def remove_from_wishlist(request, wishlist_item_id):
    print(f"remove_from_wishlist called with wishlist_item_id: {wishlist_item_id}")
    try:
        wishlist_item = get_object_or_404(
            Wishlist,
            id=wishlist_item_id,
            user=request.user
        )
        print(f"Wishlist item found: id={wishlist_item.id}, user={wishlist_item.user.username}, product={wishlist_item.variant.product.name}, variant={wishlist_item.variant.color}, size={wishlist_item.size.size if wishlist_item.size else 'None'}")
    except Exception as e:
        print(f"Error finding wishlist item: {e}")
        messages.error(request, "Wishlist item not found or does not belong to you.")
        return redirect('wishlist')

    if request.method == 'POST':
        print("POST request received for removing wishlist item")
        try:
            product_name = wishlist_item.variant.product.name
            wishlist_item.delete()
            print(f"Successfully deleted wishlist item: {wishlist_item_id}")
            messages.success(request, f"{product_name} has been removed from your wishlist.")
        except Exception as e:
            print(f"Error deleting wishlist item: {e}")
            messages.error(request, "An error occurred while removing the item from your wishlist.")
        return redirect('wishlist')
    else:
        print(f"Invalid request method: {request.method}")
        messages.error(request, "Invalid request to remove item from wishlist.")
        return redirect('wishlist')






@login_required(login_url='login')
def add_to_wishlist(request,product_id):

    if request.method == 'POST':
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


