from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from checkout.models import Order, OrderItem, Address,create_unique_order_id
from cart.models import CartItem,Cart
from decimal import Decimal
from django.http import HttpResponse
from io import BytesIO
from wallet .models import Wallet, WalletTransaction
import uuid
import logging
from django.utils import timezone
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import JsonResponse
from django.db import transaction
from coupon.models import Coupon, CouponUsage
import razorpay
from django.conf import settings
from decimal import Decimal


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def place_order(request):
    if request.method == 'POST':
        user = request.user
        cart = get_object_or_404(Cart, user=user)
        cart_items = CartItem.objects.filter(cart=cart)
        
        if not cart_items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect('cart')

        address_id = request.POST.get('address_id')
        payment_method = request.POST.get('payment_method')
        coupon_code = request.POST.get('coupon_code', None)

        if not address_id or not payment_method:
            messages.error(request, "Please select an address and payment method.")
            return redirect('checkout')

        address = get_object_or_404(Address, id=address_id, user=user)
        subtotal = sum(
                    item.variant.final_offer_price * item.quantity
                    if item.variant.final_offer_price > 0
                    else item.variant.original_price * item.quantity
                    for item in cart_items
                )

        if subtotal >= 1000:
            shipping = Decimal('0.00')
        else:
            shipping = Decimal('50.00')

        discount = Decimal('0.00')



        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                if coupon.is_valid(user, subtotal):
                    if coupon.discount_type == 'percentage':
                        discount = (coupon.discount_percentage / 100) * subtotal
                    else:
                        discount = coupon.discount_value
                    
                    CouponUsage.objects.create(user=user, coupon= coupon, times_used= 1 )
                else:
                    messages.error(request, "Invalid coupon.")
                    return redirect('checkout')
            except Coupon.DoesNotExist:
                messages.error(request, "Coupon does not exist.")
                return redirect('checkout')
            

        final_total = subtotal + shipping - discount

        for item in cart_items:
            if item.quantity > item.size.stock:
                messages.error(request, f"Insufficient stock for {item.variant.product.name} ({item.size.size}).")
                return redirect('cart')



        order_data = {
            'user_id': user.id,
            'address_id': address.id,
            'subtotal': float(subtotal),
            'shipping': float(shipping),
            'discount': float(discount),
            'total': float(final_total),
            'payment_method': payment_method,
            'coupon_code': coupon_code
        }
        request.session['order_data'] = order_data
        request.session['cart_items'] = [{
            'variant_id': item.variant.id,
            'size_id': item.size.id,
            'quantity': item.quantity
        } for item in cart_items]

        if payment_method == 'razorpay':
            try:
                razorpay_order = razorpay_client.order.create({
                    'amount': int(final_total * 100), 
                    'currency': 'INR',
                    'payment_capture': '1'  
                })
                razorpay_order_id = razorpay_order['id']
                order_data['razorpay_order_id'] = razorpay_order_id
                request.session['order_data'] = order_data  
                return redirect('payment') 
            except razorpay.errors.BadRequestError as e:
                messages.error(request, f"Razorpay error: {str(e)}")
                return redirect('checkout')

        elif payment_method == 'cod':
            with transaction.atomic():
                order = Order.objects.create(
                    user=user,
                    shipping_address=address, 
                    total_price=final_total, 
                    discount_coupon_amount=discount, 
                    payment_method=payment_method,
                    status='pending'
                )

                order.shipping = Decimal('0.00') if subtotal >= 1000 else Decimal('50.00')
                order.save()

                if coupon_code:
                    order.coupon = Coupon.objects.get(code=coupon_code)
                    order.save()

                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        size=item.size,
                        quantity=item.quantity,
                        price=item.variant.product.price
                    )
                    item.size.stock -= item.quantity
                    item.size.save()

                cart_items.delete()
                cart.delete()

                del request.session['order_data']
                del request.session['cart_items']

            messages.success(request, "Order placed successfully!")
            return redirect('order_confirmation', order_id=order.id)
        
        elif payment_method == 'wallet':
                wallet = get_object_or_404(Wallet, user=user)
                if wallet.balance < final_total:
                    messages.error(request, "Insufficient wallet balance.")
                    return redirect('checkout')

                order = Order.objects.create(
                    user=user,
                    shipping_address=address,
                    total_price=final_total,
                    discount_coupon_amount=discount,
                    payment_method='wallet',
                    status='completed'  # Wallet payments are instant
                )
                if coupon_code:
                    order.coupon = Coupon.objects.get(code=coupon_code)
                    order.save()

                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        size=item.size,
                        quantity=item.quantity,
                        price=item.variant.product.price
                    )
                    item.size.stock -= item.quantity
                    item.size.save()

                # Deduct from wallet and create transaction
                wallet.balance -= final_total
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    order=order,
                    amount=final_total,
                    transaction_type='debit',
                    status='completed',
                    description=f"Payment for Order ID: {order.id}",
                    transaction_id=str(uuid.uuid4())
                )

                cart_items.delete()
                cart.delete()

                del request.session['order_data']
                del request.session['cart_items']

                messages.success(request, "Order placed successfully using wallet!")
                return redirect('order_confirmation', order_id=order.id)
        

        
        elif payment_method == 'wallet':
                wallet = get_object_or_404(Wallet, user=user)
                if wallet.balance < final_total:
                    messages.error(request, "Insufficient wallet balance.")
                    return redirect('checkout')

                order = Order.objects.create(
                    user=user,
                    shipping_address=address,
                    total_price=final_total,
                    discount_coupon_amount=discount,
                    payment_method='wallet',
                    status='completed'  # Wallet payments are instant
                )
                if coupon_code:
                    order.coupon = Coupon.objects.get(code=coupon_code)
                    order.save()

                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        size=item.size,
                        quantity=item.quantity,
                        price=item.variant.product.price
                    )
                    item.size.stock -= item.quantity
                    item.size.save()

                # Deduct from wallet and create transaction
                wallet.balance -= final_total
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    order=order,
                    amount=final_total,
                    transaction_type='debit',
                    status='completed',
                    description=f"Payment for Order ID: {order.id}",
                    transaction_id=str(uuid.uuid4())
                )

                cart_items.delete()
                cart.delete()

                del request.session['order_data']
                del request.session['cart_items']

                messages.success(request, "Order placed successfully using wallet!")
                return redirect('order_confirmation', order_id=order.id)

        else:
            messages.error(request, "Invalid payment method.")
            return redirect('checkout')

    return redirect('checkout')



@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})    


@login_required
def order_details(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order_items = OrderItem.objects.filter(order=order)
        order_items_with_total = [
            {
                'item': item,
                'total_price': item.quantity * item.price 
            }
            for item in order_items
        ]
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('shop') 
    context = {
        'order': order,
        'order_items_with_total': order_items_with_total,  
        'cancellable_statuses': ['processing','order_placed', 'shipped', 'out_for_delivery'],
    }
    return render(request, 'order_details.html', context)



@login_required
def generate_invoice(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order_items = OrderItem.objects.filter(order=order)
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('shop') 

    buffer = BytesIO()

    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  

    p.setFont("Helvetica", 14)

    p.drawString(1 * inch, height - 1 * inch, "Invoice")
    p.setFont("Helvetica", 12)

    y_position = height - 1.5 * inch
    p.drawString(1 * inch, y_position, f"Order Reference: {order.id}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"Customer: {request.user.first_name or 'Customer'} {request.user.last_name}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"Date: {order.created_at.strftime('%B %d, %Y')}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"Payment Method: {order.payment_method}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"Payment Status: {order.payment_status}")
    y_position -= 0.5 * inch

    p.setFont("Helvetica-Bold", 12)
    p.drawString(1 * inch, y_position, "Shipping Address")
    p.setFont("Helvetica", 12)
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"{order.shipping_address.street_address or 'N/A'}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"{order.shipping_address.city or 'N/A'}, {order.shipping_address.state or 'N/A'}, {order.shipping_address.country or 'N/A'}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"Postal Code: {order.shipping_address.postal_code or 'N/A'}")
    y_position -= 0.3 * inch
    p.drawString(1 * inch, y_position, f"Phone: {order.shipping_address.phone_number or 'N/A'}")
    y_position -= 0.5 * inch

    p.setFont("Helvetica-Bold", 12)
    p.drawString(1 * inch, y_position, "Order Items")
    y_position -= 0.3 * inch
    p.setFont("Helvetica", 12)
    p.drawString(0.5 * inch, y_position, "Product")
    p.drawString(2.0 * inch, y_position, "Color")
    p.drawString(2.7 * inch, y_position, "Size")
    p.drawString(3.2 * inch, y_position, "Qty")
    p.drawString(4.2 * inch, y_position, "Total")
    y_position -= 0.2 * inch
    p.line(0.5 * inch, y_position, 5.5 * inch, y_position)
    y_position -= 0.3 * inch

    for item in order_items:
        if y_position < 1 * inch:  
            p.showPage()
            p.setFont("Helvetica", 12)
            y_position = height - 1 * inch
        p.drawString(0.5 * inch, y_position, item.size.variant.product.name or "Unknown Product")
        color = item.size.variant.color if item.size.variant and hasattr(item.size.variant, 'color') else "N/A"
        p.drawString(2.0 * inch, y_position, color)
        size = str(item.size) if item.size else "N/A"
        p.drawString(2.7 * inch, y_position, size)
        p.drawString(3.2 * inch, y_position, str(item.quantity))
        total = item.quantity * item.price
        p.drawString(4.2 * inch, y_position, f"Rs :{total:.2f}")
        y_position -= 0.3 * inch

    y_position -= 0.3 * inch
    p.setFont("Helvetica-Bold", 12)
    p.drawString(1 * inch, y_position, f"Total Amount: Rs :{order.total_price:.2f}")

    p.showPage()
    p.save()

    buffer.seek(0)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
    response.write(pdf)
    return response





                                   


logger = logging.getLogger(__name__)

@login_required
def cancel_product(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    logger.debug(f"Item ID: {item.id}, Status: {item.status}, Can cancel: {item.can_update_status('canceled')}")
    
    if item.status == 'canceled':
        messages.error(request, "This product has already been canceled.")
        return redirect('order_details', order_id=item.order.id)
    
    if not item.can_update_status('canceled'):
        messages.error(request, f"This product cannot be canceled because it is in '{item.status}' status.")
        return redirect('order_details', order_id=item.order.id)
    
    if request.method == 'POST':
        logger.debug(f"POST request received: {request.POST}")
        cancel_reason = request.POST.get('cancel_reason')
        if not cancel_reason:
            messages.error(request, "Please provide a cancellation reason.")
            return redirect('order_details', order_id=item.order.id)
        
        try:
            with transaction.atomic():
                item_total = Decimal(str(item.price)) * Decimal(str(item.quantity))
                if item_total <= 0:
                    logger.error(f"Invalid item total: Price={item.price}, Quantity={item.quantity}")
                    messages.error(request, "Cannot process refund due to invalid price or quantity.")
                    return redirect('order_details', order_id=item.order.id)
                
                order_items = OrderItem.objects.filter(order=item.order)
                order_subtotal = sum(
                    Decimal(str(oi.price)) * Decimal(str(oi.quantity))
                    for oi in order_items
                )
                
                order = item.order
                if order_subtotal > 0:
                    discount_ratio = order.total_price / order_subtotal
                else:
                    discount_ratio = Decimal('1.0')
                    logger.warning(f"Order subtotal is zero for order ID: {order.id}")
                
                refund_amount = item_total * discount_ratio
                refund_amount = refund_amount.quantize(Decimal('0.01'))  
                
                if refund_amount <= 0:
                    logger.error(f"Invalid refund amount: {refund_amount} for item ID: {item.id}")
                    messages.error(request, "Cannot process refund due to invalid amount.")
                    return redirect('order_details', order_id=item.order.id)
                
                logger.debug(f"Refund amount: {refund_amount}, Item total: {item_total}, Discount ratio: {discount_ratio}")
                
                item.status = 'canceled'
                item.cancel_reason = cancel_reason
                item.save()
                logger.debug(f"OrderItem updated: Status={item.status}, Cancel reason={item.cancel_reason}")
                
                wallet, created = Wallet.objects.get_or_create(user=request.user, defaults={'balance': 0.00})
                logger.debug(f"Wallet created: {created}, Initial balance: {wallet.balance}")
                wallet.balance += refund_amount
                wallet.save()
                updated_wallet = Wallet.objects.get(user=request.user)
                logger.debug(f"Updated wallet balance: {updated_wallet.balance}")
                
                try:
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        order=item.order,
                        amount=refund_amount,
                        transaction_type='credit',
                        status='completed',
                        description=f"Refund for canceled item: {item.size.variant.product.name or 'Unknown Product'}"
                    )
                    logger.debug("Wallet transaction created successfully")
                except Exception as e:
                    logger.error(f"Error creating wallet transaction: {str(e)}")
                    messages.error(request, f"Failed to record refund transaction: {str(e)}")
                    return redirect('order_details', order_id=item.order.id)
                
                messages.success(request, f"Product canceled and ₹{refund_amount} refunded to your wallet.")
        except Exception as e:
            logger.error(f"Error during cancellation: {str(e)}")
            messages.error(request, f"An error occurred while processing the cancellation: {str(e)}")
        return redirect('order_details', order_id=item.order.id)
    
    context = {
        'item_id': item.id,
        'order_id': item.order.id,
    }
    return render(request, 'cancel_product.html', context)



logger = logging.getLogger(__name__)

@login_required

def return_product(request, item_id):
    order_item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    logger.debug(f"Item ID: {order_item.id}, Status: {order_item.status}")

    if order_item.status != 'delivered' or (timezone.now() - order_item.updated_at).days > 7:
        messages.error(request, "This item is not eligible for return.")
        logger.info(f"Cannot return item {order_item.id} - Status: {order_item.status}, Days since update: {(timezone.now() - order_item.updated_at).days}")
        return redirect('order_details', order_id=order_item.order.id)

    if request.method == "POST":
        return_reason = request.POST.get("return_reason")
        if return_reason:
            order_item.status = 'return_requested'
            order_item.return_reason = return_reason
            order_item.return_requested_at = timezone.now()
            order_item.save()
            messages.success(request, "Return request submitted successfully.")
            logger.info(f"Return request for item {order_item.id} submitted: Reason={return_reason}")
            return redirect('order_details', order_id=order_item.order.id)
        else:
            messages.error(request, "Please provide a reason for return.")
            logger.warning(f"Return request for item {order_item.id} failed: No reason provided")
            return redirect('return_product', item_id=order_item.id)

    context = {
        'order_item': order_item,
        'item_id': order_item.id,
        'order_id': order_item.order.id,
    }
    logger.debug("Rendering return_reason.html")
    return render(request, 'return_reason.html', context)



