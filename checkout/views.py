from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from cart.models import Cart, CartItem
from user_profile.models import Address, ShippingAddress
from django.db import transaction
from decimal import Decimal
from .models import Order, OrderItem
from django.http import JsonResponse
import logging
from coupon.models import Coupon, CouponUsage
from django.utils import timezone
from datetime import datetime
from django.db.models import F
from django.db import models
from django.views.decorators.csrf import csrf_exempt
import razorpay
from django.conf import settings
from offer.models import ProductOffer, CategoryOffer
logger = logging.getLogger(__name__)
from django.db.models import Count, F
from wallet.models import Wallet, WalletTransaction




@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart')

    try:
        subtotal = Decimal('0.00')
        for item in cart_items:
            total_price = item.get_total_price()
            if total_price is None:
                messages.error(request, f"Invalid price for item {item.id}.")
                return redirect('cart')
            subtotal += total_price
    except (ValueError, TypeError) as e:
        messages.error(request, f"Error calculating subtotal: {str(e)}")
        return redirect('cart')

    shipping = Decimal('0.00') if subtotal >= Decimal('1000.00') else Decimal('40.00')
    cod_allowed = subtotal <= Decimal('1000.00') 
    discount = Decimal('0.00')
    applied_coupon = None

    coupon_code = request.session.get('coupon_code')
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            print("Applying coupon from session:", coupon.__dict__)
            min_purchase = Decimal(str(coupon.minimum_purchase_amount))
            print("Subtotal:", subtotal, "Min purchase:", min_purchase)
            if subtotal >= min_purchase:
                if coupon.discount_type == 'percentage':
                    discount_percentage = Decimal(str(coupon.discount_percentage))
                    discount = (discount_percentage / Decimal('100.00')) * subtotal
                    max_discount = Decimal(str(coupon.max_discount_amount))
                    if discount > max_discount:
                        discount = max_discount
                else:
                    discount = Decimal(str(coupon.discount_value))
                applied_coupon = coupon
                print("Discount applied:", discount)
            else:
                messages.error(request, f"Minimum purchase of ₹{min_purchase} required.")
                del request.session['coupon_code']
                request.session.modified = True
        except Coupon.DoesNotExist:
            messages.error(request, "Applied coupon does not exist.")
            del request.session['coupon_code']
            request.session.modified = True

    try:
        final_total = subtotal + shipping - discount
    except Exception as e:
        messages.error(request, f"Error calculating final total: {str(e)}")
        return redirect('cart')
    

    wallet, created = Wallet.objects.get_or_create(user=request.user, defaults={'balance': 0.00})
    wallet_balance = wallet.balance
    wallet_payment_allowed = wallet_balance >= final_total


    used_coupon_ids = CouponUsage.objects.filter(user=request.user).values_list('coupon_id', flat=True)
    available_coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_until__gt=timezone.now()
    ).exclude(
        id__in=used_coupon_ids
    ).annotate(
        usage_count=Count('usages')
    ).filter(
        usage_limit__gt=F('usage_count')
    ).order_by('-created_at')[:2]

    print("Available coupons:", list(available_coupons.values('code', 'is_active', 'valid_from', 'valid_until', 'usage_limit', 'usage_count')))

    addresses = Address.objects.filter(user=request.user)

    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'discount': discount,
        'final_total': final_total,
        'addresses': addresses,
        'available_coupons': available_coupons,
        'applied_coupon': applied_coupon,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'cod_allowed': cod_allowed, 
        'wallet_payment_allowed': wallet_payment_allowed,
        'wallet_balance': wallet_balance,

    }
    return render(request, 'checkout.html', context)





@login_required
def checkout_add_address(request):
    if request.method == 'POST':
        logger.debug(f"POST data: {request.POST}")
        try:
            phone_number = request.POST.get('phone_number')
            street_address = request.POST.get('street_address')
            city = request.POST.get('city')
            state = request.POST.get('state')
            country = request.POST.get('country')
            postal_code = request.POST.get('postal_code')
            is_default = request.POST.get('is_default') == 'on'

            required_fields = {
                'phone_number': phone_number,
                'street_address': street_address,
                'city': city,
                'state': state,
                'country': country,
                'postal_code': postal_code,
            }
            errors = {}
            for field, value in required_fields.items():
                if not value or value.strip() == '':
                    errors[field] = f"{field.replace('_', ' ').title()} is required."

            if phone_number and not phone_number.replace('+', '').isdigit():
                errors['phone_number'] = "Phone number must contain only digits and an optional '+'."

            if errors:
                for field, error in errors.items():
                    messages.error(request, error)
                    logger.warning(f"Validation error: {error}")
                return render(request, 'checkout_add_address.html', {'form_data': request.POST})

            address = Address(
                user=request.user,
                phone_number=phone_number,
                street_address=street_address,
                city=city,
                state=state,
                country=country,
                postal_code=postal_code,
                is_default=is_default
            )

            if is_default:
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

            address.save()
            logger.info(f"Address saved for user {request.user.username}: {address}")

            messages.success(request, 'Address added successfully!')
            return redirect('checkout')
        except Exception as e:
            logger.error(f"Error saving address: {str(e)}", exc_info=True)
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'checkout_add_address.html', {'form_data': request.POST})
    else:
        logger.debug("Rendering checkout_add_address.html for GET request")
        return render(request, 'checkout_add_address.html')

def checkout_edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        address.street_address = request.POST.get('street_address')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.country = request.POST.get('country')
        address.postal_code = request.POST.get('postal_code')
        address.phone_number = request.POST.get('phone_number')
        address.is_default = request.POST.get('is_default') == 'on'
        
        address.save()
        
        if address.is_default:
            Address.objects.filter(user=request.user, is_default=True).exclude(id=address.id).update(is_default=False)
        
        messages.success(request, 'Address updated successfully.')
        return redirect('checkout')
    
    return render(request, 'checkout_edit_address.html', {'address': address})

@login_required
def order_success(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('index')

    context = {'order': order}
    return render(request, 'order_success.html', context)






@login_required
def retry_payment(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id, user=request.user)
        if order.payment_status == 'Paid':
            return JsonResponse({'success': False, 'message': 'Order already paid'})

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            razorpay_order = client.order.create({
                'amount': int(order.total_price * 100), 
                'currency': 'INR',
                'payment_capture': '1'
            })
            order.razorpay_order_id = razorpay_order['id']
            order.retry_payment_attempts += 1 
            order.save()
            return JsonResponse({
                'success': True,
                'razorpay_order_id': razorpay_order['id'],
                'amount': float(order.total_price) 
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request'})



