from django.db import models
from categories.models import categories
from django.db.models.signals import pre_save,post_save,post_delete
from django.dispatch import receiver    

# Create your models here.

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(categories, on_delete=models.CASCADE, null=True, blank=True, related_name="products")   
    image = models.ImageField(upload_to='product_images/', null=True, blank=True,  default=None)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    @receiver(post_save, sender=categories)
    def update_color_products_listing_status(sender, instance, **kwargs):
    
        Product.objects.filter(category=instance).update(is_active=instance.is_listed)



class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    color = models.CharField(max_length=50)
     
    image_main = models.ImageField(upload_to='product_images/', null=True, blank=True)
    image_1 = models.ImageField(upload_to='product_images/', null=True, blank=True)
    image_2 = models.ImageField(upload_to='product_images/', null=True, blank=True)
    image_3 = models.ImageField(upload_to='product_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.color}"

class Size(models.Model):
    size = models.CharField(max_length=15)
    stock = models.BigIntegerField(default=0)
    variant = models.ForeignKey(ProductVariant, related_name="sizes", on_delete=models.CASCADE)


    def __str__(self):
        return self.size

