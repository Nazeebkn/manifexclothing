from django.db import models
from django.contrib.auth.models import User
from products.models import ProductVariant
from products.models import Size
from decimal import Decimal
from offer.models import ProductOffer, CategoryOffer
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP

def get_best_offer(product):
    """
    Returns the largest applicable discount percentage for the product.
    Considers both ProductOffer and CategoryOffer.
    Returns 0 if no valid offer is found.
    """
    now = timezone.now()
    product_offer_discount = 0
    category_offer_discount = 0

    # Check for Product Offer
    try:
        product_offer = product.product_offer.get(status='active', is_active=True)
        if product_offer.valid_from <= now <= product_offer.valid_until:
            product_offer_discount = product_offer.discount_percentage
    except ProductOffer.DoesNotExist:
        pass

    # Check for Category Offer
    if product.category:  # Ensure product has a category
        try:
            category_offer = product.category.category_offer.get(status='active', is_active=True)
            if category_offer.valid_from <= now <= category_offer.valid_until:
                category_offer_discount = category_offer.discount_percentage
        except CategoryOffer.DoesNotExist:
            pass

    # Return the largest discount
    return max(product_offer_discount, category_offer_discount)

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Discount amount applied by the coupon."
    )
    discounted_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total after applying coupon discount and shipping."
    )

    def __str__(self):
        return f"Cart for {self.user.username if self.user else 'Anonymous'}"

    def clear_discount(self):
        """Clear discount-related fields from the cart."""
        self.discount_amount = None
        self.discounted_total = None
        self.save()

    def validate_discount(self):
        """Validate discount and recalculate totals if necessary."""
        if not self.discount_amount or not self.discounted_total:
            self.clear_discount()
            return True

        # Recalculate subtotal
        subtotal = sum(item.variant.product.price * item.quantity for item in self.items.all())

        # Calculate shipping
        shipping = Decimal('50.00') if subtotal < 1000 else Decimal('0.00')

        # Verify discounted_total consistency (optional, for safety)
        # This requires coupon info, so we'll handle validation in place_order
        return True
    








    # def calculate_discount(self, coupon, subtotal):
    #     """Calculate discount based on coupon type."""
    #     if coupon.discount_type == 'percentage':
    #         discount = (coupon.discount_percentage / Decimal('100')) * subtotal
    #         return min(discount, coupon.max_discount_amount)
    #     else:  # fixed
    #         return coupon.discount_value

    # def get_final_total(self):
    #     """Calculate final total including shipping and discounts."""
    #     subtotal = sum(item.get_total_price() for item in self.items.all())
    #     shipping = Decimal('50.00') if subtotal < 1000 else Decimal('0.00')
    #     discount = self.discount_amount or Decimal('0.00')
    #     return subtotal + shipping - discount
    












class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.variant.product.name} ({self.size.size})"

    def get_total_price(self):
        if self.variant.product.price is None or self.quantity is None:
            raise ValueError("Price or quantity is not set.")
        
        # Get the original price
        original_price = Decimal(str(self.variant.product.price))
        total_price = Decimal(str(self.quantity)) * original_price

        # Apply the best offer
        best_discount = get_best_offer(self.variant.product)
        if best_discount > 0:
            discount_amount = (Decimal(str(best_discount)) / Decimal('100')) * total_price
            total_price -= discount_amount
            # Round to 2 decimal places
            total_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return total_price
        

    