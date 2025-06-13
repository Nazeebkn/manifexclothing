from django.db import models
from django.contrib.auth.models import User
from products.models import ProductVariant, Size  # Adjust the import based on where your ProductVariant and Size models are defined

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='wishlist', null=True, blank= True)
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name='wishlist', null=True, blank= True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'variant', 'size')  # Prevent duplicate wishlist entries for the same user, variant, and size

    def __str__(self):
        return f"{self.user.username} - {self.variant.product.name} ({self.variant.color})"