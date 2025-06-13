from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
import uuid

class CouponManager(models.Manager):
    def active(self):
        """Return only active coupons that are currently valid."""
        now = timezone.now()
        return self.filter(
            status='active',
            is_active=True,
            valid_from__lte=now,
            valid_until__gte=now,
            usage_limit__gt=0
        )

    def delete_coupon(self, coupon_id):
        """Safely delete a coupon by ID."""
        try:
            coupon = self.get(id=coupon_id)
            coupon.delete()
            return True
        except self.model.DoesNotExist:
            return False

class Coupon(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    )

    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique code for the coupon (e.g., SAVE10).",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the coupon."
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default='percentage',
        help_text="Type of discount: percentage or fixed amount."
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0.01, message="Discount percentage must be greater than 0."),
            MaxValueValidator(100.00, message="Discount percentage cannot exceed 100%.")
        ],
        help_text="Discount percentage (e.g., 10 for 10%). Required if discount type is percentage."
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0.01, message="Discount value must be greater than 0.")
        ],
        help_text="Discount value for fixed amount (e.g., $10). Required if discount type is fixed."
    )
    minimum_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00, message="Minimum purchase amount cannot be negative.")],
        help_text="Minimum purchase amount required to apply the coupon."
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=200.00,
        validators=[MinValueValidator(0.00, message="Maximum discount amount cannot be negative.")],
        help_text="Maximum discount amount for percentage-based coupons."
    )
    valid_from = models.DateTimeField(
        help_text="Date and time when the coupon becomes valid."
    )
    valid_until = models.DateTimeField(
        help_text="Date and time when the coupon expires."
    )
    usage_limit = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1, message="Usage limit must be at least 1.")],
        help_text="Number of times this coupon can be used."
    )
   

    is_active = models.BooleanField(
        default=True,
        help_text="Whether the coupon is active and can be used."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CouponManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"

    def clean(self):
        """Custom validation for the model."""
        # Ensure valid_from is not in the past when creating a new coupon
        if not self.pk and self.valid_from < timezone.now():
            raise ValidationError("The 'valid_from' date cannot be in the past when creating a new coupon.")

        # Ensure valid_until is after valid_from
        if self.valid_until <= self.valid_from:
            raise ValidationError("The 'valid_until' date must be after the 'valid_from' date.")

        # Validate discount fields based on discount_type
        if self.discount_type == 'percentage':
            if self.discount_percentage is None:
                raise ValidationError("Discount percentage is required for percentage-based coupons.")
            if self.discount_value is not None:
                raise ValidationError("Discount value should not be set for percentage-based coupons.")
            if self.discount_percentage < 0 or self.discount_percentage > 100:
                raise ValidationError("Discount percentage must be between 0 and 100.")
        elif self.discount_type == 'fixed':
            if self.discount_value is None:
                raise ValidationError("Discount value is required for fixed-amount coupons.")
            if self.discount_percentage is not None:
                raise ValidationError("Discount percentage should not be set for fixed-amount coupons.")
            if self.discount_value <= 0:
                raise ValidationError("Discount value must be greater than 0 for fixed-amount coupons.")

        # Ensure times_used does not exceed usage_limit
        

        # Ensure max_discount_amount is greater than 0 for percentage discounts
        if self.discount_type == 'percentage' and self.max_discount_amount <= 0:
            raise ValidationError("Maximum discount amount must be greater than 0 for percentage discounts.")

    def save(self, *args, **kwargs):
        """Override save to run full validation and update status."""
        # Run custom validations
        self.full_clean()

        # Update status based on validity dates, usage, and is_active
        now = timezone.now()
        if not self.is_active:
            self.status = 'inactive'
        elif self.valid_until < now:
            self.status = 'expired'
            

        super().save(*args, **kwargs)

    def __str__(self):
        if self.discount_type == 'percentage':
            return f"{self.code} (Percentage: {self.discount_percentage}%)"
        else:
            return f"{self.code} (Fixed: ${self.discount_value})"

    from django.utils import timezone

    from django.utils import timezone

    def can_be_used(self):
       
        now = timezone.now().date()  
        valid_from = self.valid_from.date()
        valid_until = self.valid_until.date()

        print(f"Current date: {now}")
        print(f"Valid from: {valid_from}")
        print(f"Valid until: {valid_until}")
        print(f"Is active: {self.is_active}")
        print(f"Date check: {valid_from <= now <= valid_until}")

        return (
            self.is_active and
            valid_from <= now <= valid_until 
        )
    


    def is_valid(self, user, subtotal):
       
        now = timezone.now()

        # Check if the coupon is active and within its validity period
        if not self.is_active or self.valid_from > now or self.valid_until < now:
            return False

        # Check if the coupon has reached its overall usage limit
        if self.usage_limit <= self.usages.count():
            return False

        # Check if the user has already used this coupon
        if self.usages.filter(user=user).exists():
            return False

        # Check if the subtotal meets the minimum purchase amount
        if subtotal < self.minimum_purchase_amount:
            return False

        return True



class CouponUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    used_at = models.DateTimeField(auto_now_add=True)

    times_used = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this coupon has been used."
    )

    class Meta:
        unique_together = ('user', 'coupon')
        verbose_name = "Coupon Usage"
        verbose_name_plural = "Coupon Usages"

    def __str__(self):
        return f"{self.user.username} used {self.coupon.code}"