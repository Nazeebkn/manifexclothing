from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from django.contrib.auth.decorators import user_passes_test
from products.models import Product
from categories.models import categories
from .models import ProductOffer, CategoryOffer

def is_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_admin)
def offer_list(request):
    product_offers = ProductOffer.objects.all()
    category_offers = CategoryOffer.objects.all()
    context = {
        'product_offers': product_offers,
        'category_offers': category_offers,
    }
    return render(request, 'offer_list.html', context)

@user_passes_test(is_admin)
def add_offer(request):
    errors = {}
    data = {}
    default_valid_from = timezone.now()
    default_valid_until = timezone.now() + timezone.timedelta(days=30)

    if request.method == 'POST':
        data = {
            'offer_type': request.POST.get('offer_type', ''),
            'product': request.POST.get('product', ''),
            'category': request.POST.get('category', ''),
            'discount_percentage': request.POST.get('discount_percentage', '').strip(),
            'valid_from': request.POST.get('valid_from', ''),
            'valid_until': request.POST.get('valid_until', ''),
            'is_active': request.POST.get('is_active') == 'on',
        }

        if data['offer_type'] not in ['product', 'category']:
            errors['offer_type'] = "Please select a valid offer type."

        if data['offer_type'] == 'product':
            if not data['product']:
                errors['product'] = "Please select a product."
            else:
                try:
                    Product.objects.get(id=data['product'])
                except Product.DoesNotExist:
                    errors['product'] = "Selected product does not exist."
        else: 
            if not data['category']:
                errors['category'] = "Please select a category."
            else:
                try:
                    categories.objects.get(id=data['category'])
                except categories.DoesNotExist:
                    errors['category'] = "Selected category does not exist."

        try:
            data['discount_percentage'] = float(data['discount_percentage'])
            if data['discount_percentage'] <= 0:
                errors['discount_percentage'] = "Discount percentage must be greater than 0."
            elif data['discount_percentage'] > 100:
                errors['discount_percentage'] = "Discount percentage cannot exceed 100."
        except ValueError:
            errors['discount_percentage'] = "Discount percentage must be a valid number."

        try:
            data['valid_from'] = timezone.make_aware(datetime.strptime(data['valid_from'], '%Y-%m-%dT%H:%M'))
            if data['valid_from'] < timezone.now():
                errors['valid_from'] = "The 'valid_from' date cannot be in the past."
        except ValueError:
            errors['valid_from'] = "Please enter a valid date and time for 'Valid From'."

        try:
            data['valid_until'] = timezone.make_aware(datetime.strptime(data['valid_until'], '%Y-%m-%dT%H:%M'))
            if 'valid_from' not in errors and data['valid_until'] <= data['valid_from']:
                errors['valid_until'] = "The 'valid_until' date must be after the 'valid_from' date."
        except ValueError:
            errors['valid_until'] = "Please enter a valid date and time for 'Valid Until'."

        if not errors:
            try:
                if data['offer_type'] == 'product':
                    product = Product.objects.get(id=data['product'])
                    if ProductOffer.objects.filter(product=product, status='active').exists():
                        errors['product'] = "An active offer already exists for this product."
                    else:
                        ProductOffer.objects.create(
                            product=product,
                            discount_percentage=data['discount_percentage'],
                            valid_from=data['valid_from'],
                            valid_until=data['valid_until'],
                            is_active=data['is_active']
                        )
                        messages.success(request, "Product offer added successfully!")
                        return redirect('offer_list')
                else: 
                    category = categories.objects.get(id=data['category'])
                    if CategoryOffer.objects.filter(category=category, status='active').exists():
                        errors['category'] = "An active offer already exists for this category."
                    else:
                        CategoryOffer.objects.create(
                            category=category,
                            discount_percentage=data['discount_percentage'],
                            valid_from=data['valid_from'],
                            valid_until=data['valid_until'],
                            is_active=data['is_active']
                        )
                        messages.success(request, "Category offer added successfully!")
                        return redirect('offer_list')
            except Exception as e:
                messages.error(request, f"Error adding offer: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")

    products = Product.objects.all()
    categories_list = categories.objects.all()
    context = {
        'products': products,
        'categories': categories_list,
        'data': data,
        'errors': errors,
        'default_valid_from': default_valid_from,
        'default_valid_until': default_valid_until,
    }
    return render(request, 'add_offer.html', context)

@user_passes_test(is_admin)
def edit_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    errors = {}
    data = {}

    if request.method == 'POST':
        data = {
            'discount_percentage': request.POST.get('discount_percentage', '').strip(),
            'valid_from': request.POST.get('valid_from', ''),
            'valid_until': request.POST.get('valid_until', ''),
            'is_active': request.POST.get('is_active') == 'on',
        }

        try:
            data['discount_percentage'] = float(data['discount_percentage'])
            if data['discount_percentage'] <= 0:
                errors['discount_percentage'] = "Discount percentage must be greater than 0."
            elif data['discount_percentage'] > 100:
                errors['discount_percentage'] = "Discount percentage cannot exceed 100."
        except ValueError:
            errors['discount_percentage'] = "Discount percentage must be a valid number."

        try:
            data['valid_from'] = timezone.make_aware(datetime.strptime(data['valid_from'], '%Y-%m-%dT%H:%M'))
        except ValueError:
            errors['valid_from'] = "Please enter a valid date and time for 'Valid From'."

        try:
            data['valid_until'] = timezone.make_aware(datetime.strptime(data['valid_until'], '%Y-%m-%dT%H:%M'))
            if 'valid_from' not in errors and data['valid_until'] <= data['valid_from']:
                errors['valid_until'] = "The 'valid_until' date must be after the 'valid_from' date."
        except ValueError:
            errors['valid_until'] = "Please enter a valid date and time for 'Valid Until'."

        if not errors:
            try:
                offer.discount_percentage = data['discount_percentage']
                offer.valid_from = data['valid_from']
                offer.valid_until = data['valid_until']
                offer.is_active = data['is_active']
                offer.save()
                messages.success(request, "Product offer updated successfully!")
                return redirect('offer_list')
            except Exception as e:
                messages.error(request, f"Error updating offer: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        data = {
            'discount_percentage': offer.discount_percentage,
            'valid_from': offer.valid_from,
            'valid_until': offer.valid_until,
            'is_active': offer.is_active,
        }

    context = {
        'offer': offer,
        'data': data,
        'errors': errors,
    }
    return render(request, 'edit_product_offer.html', context)

@user_passes_test(is_admin)
def edit_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    errors = {}
    data = {}

    if request.method == 'POST':
        data = {
            'discount_percentage': request.POST.get('discount_percentage', '').strip(),
            'valid_from': request.POST.get('valid_from', ''),
            'valid_until': request.POST.get('valid_until', ''),
            'is_active': request.POST.get('is_active') == 'on',
        }

        try:
            data['discount_percentage'] = float(data['discount_percentage'])
            if data['discount_percentage'] <= 0:
                errors['discount_percentage'] = "Discount percentage must be greater than 0."
            elif data['discount_percentage'] > 100:
                errors['discount_percentage'] = "Discount percentage cannot exceed 100."
        except ValueError:
            errors['discount_percentage'] = "Discount percentage must be a valid number."

        try:
            data['valid_from'] = timezone.make_aware(datetime.strptime(data['valid_from'], '%Y-%m-%dT%H:%M'))
        except ValueError:
            errors['valid_from'] = "Please enter a valid date and time for 'Valid From'."

        try:
            data['valid_until'] = timezone.make_aware(datetime.strptime(data['valid_until'], '%Y-%m-%dT%H:%M'))
            if 'valid_from' not in errors and data['valid_until'] <= data['valid_from']:
                errors['valid_until'] = "The 'valid_until' date must be after the 'valid_from' date."
        except ValueError:
            errors['valid_until'] = "Please enter a valid date and time for 'Valid Until'."

        if not errors:
            try:
                offer.discount_percentage = data['discount_percentage']
                offer.valid_from = data['valid_from']
                offer.valid_until = data['valid_until']
                offer.is_active = data['is_active']
                offer.save()
                messages.success(request, "Category offer updated successfully!")
                return redirect('offer_list')
            except Exception as e:
                messages.error(request, f"Error updating offer: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        data = {
            'discount_percentage': offer.discount_percentage,
            'valid_from': offer.valid_from,
            'valid_until': offer.valid_until,
            'is_active': offer.is_active,
        }

    context = {
        'offer': offer,
        'data': data,
        'errors': errors,
    }
    return render(request, 'edit_category_offer.html', context)

@user_passes_test(is_admin)
def delete_product_offer(request, offer_id):
    if request.method == 'POST':
        offer = get_object_or_404(ProductOffer, id=offer_id)
        try:
            offer.delete()
            messages.success(request, f"Product offer for '{offer.product.name}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting product offer: {str(e)}")
    else:
        messages.error(request, "Invalid request method. Please use the delete button to remove an offer.")
    return redirect('offer_list')

@user_passes_test(is_admin)
def delete_category_offer(request, offer_id):
    if request.method == 'POST':
        offer = get_object_or_404(CategoryOffer, id=offer_id)
        try:
            offer.delete()
            messages.success(request, f"Category offer for '{offer.category.name}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting category offer: {str(e)}")
    else:
        messages.error(request, "Invalid request method. Please use the delete button to remove an offer.")
    return redirect('offer_list')