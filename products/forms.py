from django import forms
from django.core.validators import MinValueValidator, RegexValidator
from django.db.models import Q
from decimal import Decimal
from .models import Product, ProductVariant, Size
import re
from django.core.exceptions import ValidationError

class ProductForm(forms.ModelForm):
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.01'), message='Price must be greater than 0')
        ],
        error_messages={
            'required': 'Price is required',
            'invalid': 'Please enter a valid price',
            'max_digits': 'Price cannot exceed 10 digits',
            'max_decimal_places': 'Price cannot have more than 2 decimal places'
        }
    )
    name = forms.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-_]+$',
                message='Name can only contain letters, numbers, spaces, hyphens and underscores'
            )
        ],
        error_messages={
            'required': 'Product name is required',
            'max_length': 'Name cannot exceed 100 characters'
        }
    )
    
    description = forms.CharField(
        widget=forms.Textarea,
        min_length=10,
        max_length=1000,
        error_messages={
            'required': 'Description is required',
            'min_length': 'Description must be at least 10 characters',
            'max_length': 'Description cannot exceed 1000 characters'
        }
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'category', 'image','price'] 

    def clean_name(self):
        name = self.cleaned_data.get('name')
        instance = getattr(self, 'instance', None)
        existing_product = Product.objects.filter(name__iexact=name) 
        
        if instance and instance.pk:
            existing_product = existing_product.exclude(pk=instance.pk)
            
        if existing_product.exists():
            raise forms.ValidationError('A product with this name already exists')
        
    def clean_name(self):
        name = self.cleaned_data['name']

        if not re.match(r'^[A-Za-z\s]+$', name):
            raise ValidationError('Product name must contain only letters and spaces. Numbers or special characters are not allowed.')
        return name
            
        return name

    def clean_image(self):  
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image file size cannot exceed 5MB')
            
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            ext = str(image.name).lower()[-5:]
            if not any(ext.endswith(x) for x in valid_extensions):
                raise forms.ValidationError('Unsupported file extension. Please use JPG, JPEG, PNG or WebP')
        
        return image

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('image'):
            raise forms.ValidationError('Product image is required')
        
        return cleaned_data

class ProductVariantForm(forms.ModelForm):
   

    color = forms.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z\s]+$',
                message='Color can only contain letters and spaces'
            )
        ],
        error_messages={
            'required': 'Color is required',
            'max_length': 'Color cannot exceed 50 characters'
        }
    )

    class Meta:
        model = ProductVariant
        fields = ['color', 'image_main', 'image_1', 'image_2', 'image_3','product'] 
        widgets = {
            'color': forms.TextInput(attrs={'placeholder': 'e.g., Red'}),
        }

    def clean_image_main(self):
        image = self.cleaned_data.get('image_main')
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image file size cannot exceed 5MB')
            
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            ext = str(image.name).lower()[-5:]
            if not any(ext.endswith(x) for x in valid_extensions):
                raise forms.ValidationError('Unsupported file extension. Please use JPG, JPEG, PNG or WebP')
        
        return image
    def __init__(self, *args, **kwargs):
        selected_product = kwargs.pop('product', None)
        super(ProductVariantForm, self).__init__(*args, **kwargs)

        self.fields['image_1'].required = False
        self.fields['image_2'].required = False
        self.fields['image_3'].required = False

        if selected_product:
            self.fields['product'].queryset = Product.objects.filter(id=selected_product.id)
            self.fields['product'].initial = selected_product
            self.fields['product'].widget = forms.HiddenInput()



class SizeForm(forms.ModelForm):
    SIZE_CHOICES = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]

    size = forms.ChoiceField(
        choices=SIZE_CHOICES,
        error_messages={
            'required': 'Size is required',
            'invalid_choice': 'Please select a valid size: S, M, L, XL, XXL'
        }
    )

    stock = forms.IntegerField(
        min_value=0,
        error_messages={
            'required': 'Stock is required',
            'min_value': 'Stock cannot be negative'
        }
    )

    class Meta:
        model = Size
        fields = ['size', 'stock', 'variant']

    def __init__(self, *args, **kwargs):
        self.selected_variant = kwargs.pop('variant', None)
        super().__init__(*args, **kwargs)
        if self.selected_variant:
            self.fields['variant'].queryset = ProductVariant.objects.filter(id=self.selected_variant.id)
            self.fields['variant'].initial = self.selected_variant
            self.fields['variant'].widget = forms.HiddenInput()
        self.fields['variant'].required = False

    def clean(self):
        cleaned_data = super().clean()
        size = cleaned_data.get('size')
        variant = cleaned_data.get('variant') or self.selected_variant

        if size and variant:
            if Size.objects.filter(variant=variant, size=size).exists():
                self.add_error('size', 'This size already exists for the variant.')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.selected_variant:
            instance.variant = self.selected_variant
        else:
            raise ValueError("Cannot save Size without a variant.")
        if commit:
            instance.save()
        return instance