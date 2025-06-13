from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import  ProductVariant, Size, Cart, CartItem
from django.db.models import Q
from django.views.decorators.cache import never_cache
import logging
import json



# Add to Cart
logger = logging.getLogger(__name__)

@login_required
def add_to_cart(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id, product__is_active=True)

    if request.method == 'POST':
        size_id = request.POST.get('size_id')

        if not size_id:
            messages.error(request, "Please select a size before adding to cart.")
            return redirect('product_details', variant_id=variant.id)

        size = get_object_or_404(Size, id=size_id, variant=variant)

        if not size.stock or size.stock <= 0:
            messages.error(request, f"Size {size.size} is out of stock for {variant.product.name} ({variant.color}).")
            return redirect('product_details', variant_id=variant.id)

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
                return redirect('product_details', variant_id=variant.id)

        messages.success(request, f"{variant.product.name} added to your cart.")
        return redirect('cart') 

    return redirect('product_details', variant_id=variant.id)

# Cart View
@login_required
def cart_view(request):
    try:
   
        cart,created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all().filter(variant__product__is_active=True)
        total = sum(item.get_total_price() for item in cart_items)
        return render(request, 'cart.html', {'cart_items': cart_items, 'total': total})
    except:
        return render(request, 'cart.html')


@never_cache
@login_required
def update_cart_quantity(request, item_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

  
    try:
        data = json.loads(request.body)
        action = data.get('action')
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid JSON data.'}, status=400)

    print(f"Action: {action}, Item ID: {item_id}, Quantity: {cart_item.quantity}")  # Debugging

    if action not in ['increment', 'decrement']:
        return JsonResponse({'success': False, 'message': 'Invalid action.'}, status=400)

    if action == 'increment':
        if cart_item.size.stock is None or cart_item.quantity + 1 > cart_item.size.stock:
            return JsonResponse({'success': False, 'message': 'Cannot add more items than available in stock.'})
        if cart_item.quantity + 1 > 10:
            return JsonResponse({'success': False, 'message': 'Maximum quantity limit reached.'})
        cart_item.quantity += 1
    elif action == 'decrement':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            cart_item.delete()
            return JsonResponse({'success': True, 'message': 'Item removed from cart.'})

    try:
        cart_item.save()
        cart_item.refresh_from_db() 
        print(f"Quantity after save: {cart_item.quantity}") 
    except Exception as e:
        print(f"Save error: {e}")
        return JsonResponse({'success': False, 'message': 'Failed to save item.'}, status=500)

    total = sum(item.get_total_price() for item in cart_item.cart.items.all())
    response = JsonResponse({
        'success': True,
        'quantity': cart_item.quantity,
        'item_total': cart_item.get_total_price(),
        'cart_total': total
    })
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# Remove from Cart
@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Product removed from cart.")
    return redirect('cart')








