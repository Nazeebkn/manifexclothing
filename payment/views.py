from django.shortcuts import render
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from user_profile.models import Address
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
import json
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from checkout.models import Order, OrderItem
from coupon.models import Coupon
from products.models import ProductVariant,Size
from cart.models import Cart, CartItem
from django.utils import timezone
# Create your views here.

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def payment(request):
    order_data = request.session.get('order_data')
    print('testttt', order_data)
    if not order_data or order_data.get('payment_method') != 'razorpay':
        messages.error(request, "Invalid payment session.")
        return redirect('checkout')

    # Add created_at as a string to order_data
    order_data['created_at'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    request.session['order_data'] = order_data

    context = {
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': order_data.get('razorpay_order_id'),
        'amount': int(order_data['total'] * 100),  # Amount in paise
        'currency': 'INR',
        'name': request.user.get_full_name() or request.user.username,
        'email': request.user.email,
        'contact': Address.objects.get(id=order_data['address_id']).phone_number,
        'total': order_data['subtotal']
    }
    return render(request, 'payment.html', context)

@csrf_exempt
def verify_payment(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'User not authenticated.'}, status=401)

    if request.method == 'POST':
        data = json.loads(request.body)
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')

        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
        except razorpay.errors.SignatureVerificationError:
            # Store order_data in session for failure page
            order_data = request.session.get('order_data', {})
            messages.error(request, "Payment verification failed. Invalid signature.")
            return JsonResponse({'success': False, 'message': 'Invalid payment signature.', 'redirect': 'order_failure'})

        order_data = request.session.get('order_data')
        cart_items_data = request.session.get('cart_items')

        if not order_data or not cart_items_data:
            messages.error(request, "Order data not found.")
            return JsonResponse({'success': False, 'message': 'Order data not found.', 'redirect': 'order_failure'})

        print('testttt', order_data['subtotal'], order_data['discount'], order_data['total'])

        with transaction.atomic():
            address = get_object_or_404(Address, id=order_data['address_id'])
            order = Order.objects.create(
                user=request.user,
                shipping_address=address,
                total_price=order_data['subtotal'],
                discount_coupon_amount=order_data['discount'],
                payment_method='razorpay',
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                status='confirmed',
                payment_status='Paid'
            )
            if order_data.get('coupon_code'):
                order.coupon = Coupon.objects.get(code=order_data['coupon_code'])
                order.save()

            for item_data in cart_items_data:
                variant = get_object_or_404(ProductVariant, id=item_data['variant_id'])
                size = get_object_or_404(Size, id=item_data['size_id'])
                quantity = item_data['quantity']
                if size.stock < quantity:
                    raise ValidationError(f"Insufficient stock for {variant.product.name} ({size.size}).")
                OrderItem.objects.create(
                    order=order,                 
                    size=size,
                    quantity=quantity,
                    price=variant.product.price
                )
                size.stock -= quantity
                size.save()

            CartItem.objects.filter(cart__user=request.user).delete()
            Cart.objects.filter(user=request.user).delete()

            del request.session['order_data']
            del request.session['cart_items']

        return JsonResponse({'success': True, 'message': 'Payment successful.', 'order_id': order.id})

    messages.error(request, "Invalid request method.")
    return JsonResponse({'success': False, 'message': 'Invalid request.', 'redirect': 'order_failure'})

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'payment_success.html', {'order': order})

@login_required
def order_failure(request):
    order_data = request.session.get('order_data', {})
    if not order_data:
        messages.error(request, "No order data available.")
        return redirect('checkout')
    
    # Parse created_at from string to datetime if needed, or use current time
    created_at = timezone.now()
    if 'created_at' in order_data:
        from datetime import datetime
        try:
            created_at = datetime.strptime(order_data['created_at'], '%Y-%m-%d %H:%M:%S')
            # If timezone support is needed, make it timezone-aware
            created_at = timezone.make_aware(created_at, timezone.get_current_timezone())
        except ValueError:
            pass  # Fallback to current time if parsing fails

    context = {
        'order_data': order_data,
        'created_at': created_at
    }
    return render(request, 'payment_failure.html', context)