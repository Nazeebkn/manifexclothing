from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from products.models import Product
from categories.models import categories

class ProductOffer(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_offer')
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[
            MinValueValidator(0.01, message="Discount percentage must be greater than 0."),
            MaxValueValidator(100.00, message="Discount percentage cannot exceed 100%.")
        ]
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Product Offer"
        verbose_name_plural = "Product Offers"
        # Ensure only one active offer per product
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(status='active'),
                name='unique_active_product_offer'
            )
        ]

    def clean(self):
        if self.valid_until <= self.valid_from:
            raise ValidationError("The 'valid_until' date must be after the 'valid_from' date.")

    def save(self, *args, **kwargs):
        self.full_clean()
        now = timezone.now()
        if not self.is_active:
            self.status = 'inactive'
        elif self.valid_until < now:
            self.status = 'expired'
        else:
            self.status = 'active'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}%"

class CategoryOffer(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    )

    category = models.ForeignKey(categories, on_delete=models.CASCADE, related_name='category_offer')
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[
            MinValueValidator(0.01, message="Discount percentage must be greater than 0."),
            MaxValueValidator(100.00, message="Discount percentage cannot exceed 100%.")
        ]
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Category Offer"
        verbose_name_plural = "Category Offers"
        # Ensure only one active offer per category
        constraints = [
            models.UniqueConstraint(
                fields=['category'],
                condition=models.Q(status='active'),
                name='unique_active_category_offer'
            )
        ]

    def clean(self):
        if self.valid_until <= self.valid_from:
            raise ValidationError("The 'valid_until' date must be after the 'valid_from' date.")

    def save(self, *args, **kwargs):
        self.full_clean()
        now = timezone.now()
        if not self.is_active:
            self.status = 'inactive'
        elif self.valid_until < now:
            self.status = 'expired'
        else:
            self.status = 'active'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} - {self.discount_percentage}%"
