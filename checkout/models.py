import uuid
from django.db import models
from django.contrib.auth.models import User
from products.models import Product, ProductVariant, Size
# from coupons.models import Coupon, CouponUsage
from user_profile.models import Address, ShippingAddress
from django.utils import timezone
from datetime import datetime
import logging





logger = logging.getLogger(__name__)

def create_unique_order_id():
    max_attempts = 10
    for _ in range(max_attempts):
        date_part = timezone.now().strftime("%Y%m%d")
        random_part = uuid.uuid4().hex[:6].upper()
        order_id = f"ORD-{date_part}-{random_part}"
        # Check if order exists without creating a new instance
        if not Order.objects.filter(id=order_id).exists():
            return order_id
    raise ValueError("Failed to generate unique order ID.")


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('pending', 'Pending'),
        ('completed', 'Completed'), 
        ('canceled', 'Canceled'),
        ('returned', 'Returned')
    ]

    id = models.CharField(primary_key=True, max_length=50, editable=False)  # Custom order ID
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    payment_method = models.CharField(max_length=20)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, default='Pending')
    # coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    discount_applied = models.BooleanField(default=False)
    discount_coupon_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance_refund = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='processing')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    retry_payment_attempts = models.PositiveIntegerField(default=0) 
    manual_status_update = models.BooleanField(default=False)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)


    def _str_(self):
        return f"Order #{self.id} - {self.user.username}"
    

    def can_update_status(self, new_status):
        allowed_transitions = {
            'processing': ['pending', 'canceled'],
            'pending': ['completed', 'canceled'],
            'completed': ['returned'],
            'canceled': [],
            'returned': [],
        }
        return new_status in allowed_transitions.get(self.status, [])
    

   


    def save(self, *args, **kwargs):
    
        if not self.id:
            max_attempts = 10
            for _ in range(max_attempts):
                date_part = timezone.now().strftime("%Y%m%d")
                random_part = uuid.uuid4().hex[:6].upper()
                order_id = f"ORD-{date_part}-{random_part}"
                
                if not Order.objects.filter(id=order_id).exists():
                    self.id = order_id
                    break
            else:
                raise ValueError("Failed to generate unique order ID.")
        
        super().save(*args, **kwargs)
        
      


    def update_order(self):
        order_items = self.items.all()
        if not order_items.exists():
            self.status = 'canceled'
            self.save()
            return

        final_states = ['delivered', 'canceled', 'return_requested', 'return', 'return_denied']
        all_items_in_final_state = all(item.status in final_states for item in order_items)

        print(f"All items in final state: {all_items_in_final_state}")

        if all_items_in_final_state:
            canceled_count = sum(1 for item in order_items if item.status == 'canceled')
            delivered_count = sum(1 for item in order_items if item.status == 'delivered')
            returned_count = sum(1 for item in order_items if item.status == 'return')
            total_items = len(order_items)

            print(f"Canceled items: {canceled_count}, Delivered items: {delivered_count}, Returned items: {returned_count}")

            if canceled_count == total_items:
                print("All items are either canceled or returned. Setting order status to 'canceled'.")
                self.status = 'canceled'
            elif canceled_count + returned_count == total_items and returned_count >= 1 and canceled_count >= 1:
                print("All items are either canceled or returned. Setting order status to 'canceled'.")
                self.status = 'canceled'
            elif returned_count == total_items:
                print("All items are returned. Setting order status to 'returned'.")
                self.status = 'returned'
                
            elif delivered_count == total_items:
                print("All items are delivered. Setting order status to 'completed'.")
                self.status = 'completed'
            else:
                print("Mixed final states. Setting order status to 'completed'.")
                self.status = 'completed' 
        else:
            print("Not all items are in final states. Setting order status to 'pending'.")
            self.status = 'pending'

        self.save(update_fields=['status'])
        print(f"Updated order status: {self.status}")



class OrderItem(models.Model):
    ORDER_ITEM_STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('order_placed', 'Order Placed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out For Delivery'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
        ('return_requested', 'Return Requested'),
       
        ('return', 'Return'),
        ('return_denied', 'Return Denied'),
    ]

    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=ORDER_ITEM_STATUS_CHOICES, default='order_placed')
    cancel_reason = models.TextField(blank=True, null=True)
    return_reason = models.TextField(blank=True, null=True)
    return_requested_at = models.DateTimeField(blank=True, null=True)
    returned_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    final_offer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def _str_(self):
        return f"{self.quantity} x {self.product.name}"

    def can_update_status(self, new_status):
        allowed_transitions = {
            'processing': ['order_placed', 'shipped', 'delivered', 'canceled'],
            'order_placed': ['shipped', 'delivered', 'canceled'],
            'shipped': ['out_for_delivery', 'delivered', 'canceled'],
            'out_for_delivery': ['delivered', 'canceled'],
            'delivered': ['return_requested'],
            'canceled': [],
            'return_requested': ['return', 'return_denied'],
            'return': ['returned'],
            'returned': [],
            'return_denied': [],
        }
        result = new_status in allowed_transitions.get(self.status, [])
        logger.debug(f"Checking status transition for OrderItem {self.id}: {self.status} -> {new_status}, Allowed: {result}")
        return result