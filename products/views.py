from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Product, ProductVariant
from .forms import ProductForm, ProductVariantForm, SizeForm
from categories.models import categories
import os
import re
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from products.models import Size
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from products.models import Product, ProductVariant, Size
from offer.models import ProductOffer, CategoryOffer

@staff_member_required
@never_cache
def product_list(request):
    search_query = request.GET.get('search', '')
    
    if search_query:
        products = Product.objects.filter(name__icontains=search_query)
    else:
        products = Product.objects.all().order_by('-id')
    
    paginator = Paginator(products, 10)  
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'page_obj': page_obj,  
        'search_query': search_query,  
    }
    
    return render(request, 'product_list.html', context)

@never_cache
@staff_member_required
def toggle_product_status(request, product_id):
    if request.method == 'POST':
        print("hello")
        product = get_object_or_404(Product, id=product_id)
        product.is_active = not product.is_active
        product.save()
        messages.success(request, f"Product {Product.name} {'activated' if Product.is_active else 'deactivated'} successfully.")
        return redirect('product_list')

@never_cache
@staff_member_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, "Product added successfully, please add variants.")
            return redirect('manage_variants', product_id=product.id)  
    else:
        form = ProductForm()
    Categories = categories.objects.all()
    return render(request, 'add_product.html', {'form': form, 'categories': Categories})

@never_cache
@staff_member_required

def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    category_list = categories.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name')
        if not re.match(r'^[A-Za-z\s]+$', name):
            custom_error_message = 'Product name must contain only letters and spaces. Numbers or special characters are not allowed.'
            return render(request, 'edit_product.html', {
                'product': product,
                'categories': category_list,
                'name_error': custom_error_message,
                'name': name,
                'description': description,
                'category_id': category_id
            })
        description = request.POST.get('description')
        category_id = request.POST.get('category')
        image = request.FILES.get('image')
        if image:
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif','.webp']
            ext = os.path.splitext(image.name)[1].lower()

            if ext not in valid_extensions:
                messages.error(request, "Only image files (.jpg, .jpeg, .png, .gif) are allowed.")
                return render(request, 'edit_product.html', {'product': product, 'categories': category_list})

        product.name = name
        product.description = description
        product.category_id = category_id

        if image:
            product.image = image  

        product.save()
        messages.success(request, 'Product updated successfully.')
        return redirect('product_list')

    return render(request, 'edit_product.html', {'product': product, 'categories': category_list})





def product_details(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    variants = ProductVariant.objects.filter(product=variant.product)
    sizes = Size.objects.filter(variant=variant)
    
    current_datetime = timezone.now() 
    print(f"Current datetime: {current_datetime}")
    

    product_offer = ProductOffer.objects.filter(
        product=variant.product,
        is_active=True,
        valid_from__lte=current_datetime,
        valid_until__gte=current_datetime
    ).exclude(status='expired').first()
    print(f"Product Offer: {product_offer}")
    


    category_offer = CategoryOffer.objects.filter(
        category=variant.product.category,
        is_active=True,
        valid_from__lte=current_datetime,
        valid_until__gte=current_datetime
    ).exclude(status='expired').first()
    print(f"Category Offer: {category_offer}")

    original_price = variant.product.price
    discounted_price = original_price
    applied_discount = 0

    if product_offer:
        discount = (product_offer.discount_percentage / 100) * original_price
        discounted_price = original_price - discount
        discounted_price = discounted_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        applied_discount = product_offer.discount_percentage

    if category_offer:
        category_discount = (category_offer.discount_percentage / 100) * original_price
        category_discounted_price = original_price - category_discount
        category_discounted_price = category_discounted_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if not product_offer or category_offer.discount_percentage > product_offer.discount_percentage:
            discounted_price = category_discounted_price
            applied_discount = category_offer.discount_percentage

    print(f"Original Price: {original_price}, Discounted Price: {discounted_price}, Applied Discount: {applied_discount}%")

    return render(request, 'product_details.html', {
        'product': variant,
        'variants': variants,
        'sizes': sizes,
        'product_offer': product_offer,
        'category_offer': category_offer,
        'original_price': original_price,
        'discounted_price': discounted_price,
        'applied_discount': applied_discount,
    })



def shop(request):
    variant_ids = (
    ProductVariant.objects
    .filter(product__is_active=True)
    .order_by('product_id', 'id')
    .distinct('product_id')
    .values_list('id', flat=True)
)
    products = ProductVariant.objects.filter(id__in=variant_ids).select_related('product')

    try:
        if request.user.is_authenticated:
            user = request.user
        else:
            
            user = None
    except Exception as e:
        pass


    for i in products:
        try:
            
            _ = i.product.image.path  
        except Exception as e:
            continue


    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(product__category__id=category_id)


    price_range = request.GET.get('price_range')
    if price_range:
        try:
            price_min, price_max = map(int, price_range.split('-'))
            products = products.filter(product__price__gte=price_min, product__price__lte=price_max)
        except ValueError:
            pass



    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min and price_min.isdigit():
        products = products.filter(price__gte=price_min)
    if price_max and price_max.isdigit():
        products = products.filter(price__lte=price_max)

    sort = request.GET.get('sort', 'default')
    if sort == 'price-desc':
        products = products.order_by('-product__price')
    elif sort == 'price-asc':
        products = products.order_by('product__price')
    elif sort == 'name-asc':
        products = products.order_by('product__name')
    elif sort == 'name-desc':
        products = products.order_by('-product__name')
    else:
        products = products.order_by('product__name') 

    paginator = Paginator(products, 8) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    Categories = categories.objects.filter(is_listed=True)
    return render(request, 'shop_grid.html', {
        'products': page_obj,
        'page_obj': page_obj,
        'categories': Categories,
    })



@staff_member_required
def variant_list(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variants = ProductVariant.objects.filter(product__id=product.id)
    return render(request, 'variants_list.html', {
        'product': product,
        'variants': variants
    })

@staff_member_required
def add_variant(request, product_id):
    selected_product = Product.objects.get(id=product_id)
    variants = selected_product.variants.all()


    if request.method == 'POST':
        form = ProductVariantForm(request.POST,request.FILES,product=selected_product)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = selected_product
            variant.save()
            messages.success(request, 'Variant added successfully.')
            return render(request ,'variants_list.html', {'variants': variants,'product':selected_product})
        else:
            messages.error(request, 'Error adding variant. Please check the form.')
    else:
        form = ProductVariantForm(product=selected_product)
    return render(request, 'add_variant.html', {
        'form': form,
        'product': selected_product
        
    })



@staff_member_required
def add_size(request, variant_id):
    selected_variant = ProductVariant.objects.get(id=variant_id)


    if request.method == 'POST':
        form = SizeForm(request.POST, variant=selected_variant)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.variant = selected_variant
            variant.save()
            messages.success(request, 'Variant added successfully.')
            return redirect('variant_list',product_id=selected_variant.product.id)
        else:
            messages.error(request, 'Error adding variant. Please check the form.')
    else:
        form = SizeForm( variant=selected_variant)
    return render(request, 'add_size.html', {
        'form': form,
        'product': selected_variant
        
    })




@staff_member_required
def edit_variant(request, product_id, variant_id):
    Product = get_object_or_404(Product, id=product_id)
    variant = get_object_or_404(ProductVariant, id=variant_id, product=Product)
    if request.method == 'POST':
        form = ProductVariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Variant updated successfully.')
            return redirect('variant_list', product_id=Product.id)
        else:
            messages.error(request, 'Error updating variant. Please check the form.')
    else:
        form = ProductVariantForm(instance=variant)
    return render(request, 'edit_variant.html', {
        'form': form,
        'product': Product,
        'variant': variant
    })

@staff_member_required
def delete_variant(request, product_id, variant_id):
    Product = get_object_or_404(Product, id=product_id)
    variant = get_object_or_404(ProductVariant, id=variant_id, product=Product)
    if request.method == 'POST':
        variant.delete()
        messages.success(request, 'Variant deleted successfully.')
        return redirect('variant_list', product_id=Product.id)
    return redirect('variant_list', product_id=Product.id)
