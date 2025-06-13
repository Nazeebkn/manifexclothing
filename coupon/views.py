from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from .models import Coupon
from django.http import JsonResponse
import json
from django.contrib.auth.decorators import login_required
from cart.models import Cart  
from coupon.models import Coupon, CouponUsage
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt

def coupon(request):
    coupons = Coupon.objects.all()

    search_query = request.GET.get('search', '')
    if search_query:
        coupons = coupons.filter(
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )

   
    paginator = Paginator(coupons, 10)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
       
        page_obj = paginator.page(1)
    except EmptyPage:
       
        page_obj = paginator.page(paginator.num_pages)

    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }

    return render(request, 'coupon.html', context)

def add_coupon(request):
    errors = {}
    data = {}

    
    default_valid_from = timezone.now()
    default_valid_until = timezone.now() + timezone.timedelta(days=30)
    default_data = {
        'minimum_purchase_amount': '0.00',
        'max_discount_amount': '200.00',
        'usage_limit': '1',
        'is_active': True,
    }

    if request.method == 'POST':
        data = {
            'code': request.POST.get('code', '').strip(),
            'description': request.POST.get('description', '').strip() or None,
            'discount_type': request.POST.get('discount_type', ''),
            'discount_percentage': request.POST.get('discount_percentage', '').strip() or None,
            'discount_value': request.POST.get('discount_value', '').strip() or None,
            'minimum_purchase_amount': request.POST.get('minimum_purchase_amount', '').strip(),
            'max_discount_amount': request.POST.get('max_discount_amount', '').strip(),
            'valid_from': request.POST.get('valid_from', ''),
            'valid_until': request.POST.get('valid_until', ''),
            'usage_limit': request.POST.get('usage_limit', '').strip(),
            'is_active': request.POST.get('is_active') == 'on',
        }

        if not data['code']:
            errors['code'] = "Coupon code is required."
        elif len(data['code']) > 50:
            errors['code'] = "Coupon code cannot exceed 50 characters."
        elif Coupon.objects.filter(code=data['code']).exists():
            errors['code'] = "A coupon with this code already exists."

        if data['discount_type'] not in ['percentage', 'fixed']:
            errors['discount_type'] = "Please select a valid discount type."

        try:
            if data['discount_percentage']:
                data['discount_percentage'] = float(data['discount_percentage'])
                if data['discount_percentage'] <= 0:
                    errors['discount_percentage'] = "Discount percentage must be greater than 0."
                elif data['discount_percentage'] > 100:
                    errors['discount_percentage'] = "Discount percentage cannot exceed 100."
            else:
                data['discount_percentage'] = None
        except ValueError:
            errors['discount_percentage'] = "Discount percentage must be a valid number."

        try:
            if data['discount_value']:
                data['discount_value'] = float(data['discount_value'])
                if data['discount_value'] <= 0:
                    errors['discount_value'] = "Discount value must be greater than 0."
            else:
                data['discount_value'] = None
        except ValueError:
            errors['discount_value'] = "Discount value must be a valid number."

        if data['discount_type'] == 'percentage':
            if data['discount_percentage'] is None:
                errors['discount_percentage'] = "Discount percentage is required for percentage-based coupons."
            if data['discount_value'] is not None:
                errors['discount_value'] = "Discount value should not be set for percentage-based coupons."
        elif data['discount_type'] == 'fixed':
            if data['discount_value'] is None:
                errors['discount_value'] = "Discount value is required for fixed-amount coupons."
            if data['discount_percentage'] is not None:
                errors['discount_percentage'] = "Discount percentage should not be set for fixed-amount coupons."

        try:
            data['minimum_purchase_amount'] = float(data['minimum_purchase_amount'])
            if data['minimum_purchase_amount'] < 0:
                errors['minimum_purchase_amount'] = "Minimum purchase amount cannot be negative."
        except ValueError:
            errors['minimum_purchase_amount'] = "Minimum purchase amount must be a valid number."

        try:
            data['max_discount_amount'] = float(data['max_discount_amount'])
            if data['max_discount_amount'] < 0:
                errors['max_discount_amount'] = "Maximum discount amount cannot be negative."
            if data['discount_type'] == 'percentage' and data['max_discount_amount'] <= 0:
                errors['max_discount_amount'] = "Maximum discount amount must be greater than 0 for percentage discounts."
        except ValueError:
            errors['max_discount_amount'] = "Maximum discount amount must be a valid number."

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

        try:
            data['usage_limit'] = int(data['usage_limit'])
            if data['usage_limit'] < 1:
                errors['usage_limit'] = "Usage limit must be at least 1."
        except ValueError:
            errors['usage_limit'] = "Usage limit must be a valid integer."

        if not errors:
            try:
                coupon = Coupon(
                    code=data['code'],
                    description=data['description'],
                    discount_type=data['discount_type'],
                    discount_percentage=data['discount_percentage'],
                    discount_value=data['discount_value'],
                    minimum_purchase_amount=data['minimum_purchase_amount'],
                    max_discount_amount=data['max_discount_amount'],
                    valid_from=data['valid_from'],
                    valid_until=data['valid_until'],
                    usage_limit=data['usage_limit'],
                    is_active=data['is_active'],
                )
                coupon.save()
                messages.success(request, "Coupon added successfully!")
                return redirect('coupon')
            except Exception as e:
                messages.error(request, f"Error saving coupon: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        data = default_data.copy()
        data['valid_from'] = default_valid_from
        data['valid_until'] = default_valid_until

    context = {
        'data': data,
        'errors': errors,
        'default_valid_from': default_valid_from,
        'default_valid_until': default_valid_until,
    }
    return render(request, 'add_coupons.html', context)





def edit_coupon(request, id):
    coupon = get_object_or_404(Coupon, id=id)
    errors = {}
    data = {}

    if request.method == 'POST':
        data = {
            'code': request.POST.get('code', '').strip(),
            'description': request.POST.get('description', '').strip() or None,
            'discount_type': request.POST.get('discount_type', ''),
            'discount_percentage': request.POST.get('discount_percentage', '').strip() or None,
            'discount_value': request.POST.get('discount_value', '').strip() or None,
            'minimum_purchase_amount': request.POST.get('minimum_purchase_amount', '').strip(),
            'max_discount_amount': request.POST.get('max_discount_amount', '').strip(),
            'valid_from': request.POST.get('valid_from', ''),
            'valid_until': request.POST.get('valid_until', ''),
            'usage_limit': request.POST.get('usage_limit', '').strip(),
            'is_active': request.POST.get('is_active') == 'on',
        }

        
        if not data['code']:
            errors['code'] = "Coupon code is required."
        elif len(data['code']) > 50:
            errors['code'] = "Coupon code cannot exceed 50 characters."
        elif Coupon.objects.filter(code=data['code']).exclude(id=coupon.id).exists():
            errors['code'] = "A coupon with this code already exists."

        if data['discount_type'] not in ['percentage', 'fixed']:
            errors['discount_type'] = "Please select a valid discount type."

        try:
            if data['discount_percentage']:
                data['discount_percentage'] = float(data['discount_percentage'])
                if data['discount_percentage'] <= 0:
                    errors['discount_percentage'] = "Discount percentage must be greater than 0."
                elif data['discount_percentage'] > 100:
                    errors['discount_percentage'] = "Discount percentage cannot exceed 100."
            else:
                data['discount_percentage'] = None
        except ValueError:
            errors['discount_percentage'] = "Discount percentage must be a valid number."

        try:
            if data['discount_value']:
                data['discount_value'] = float(data['discount_value'])
                if data['discount_value'] <= 0:
                    errors['discount_value'] = "Discount value must be greater than 0."
            else:
                data['discount_value'] = None
        except ValueError:
            errors['discount_value'] = "Discount value must be a valid number."

        if data['discount_type'] == 'percentage':
            if data['discount_percentage'] is None:
                errors['discount_percentage'] = "Discount percentage is required for percentage-based coupons."
            if data['discount_value'] is not None:
                errors['discount_value'] = "Discount value should not be set for percentage-based coupons."
        elif data['discount_type'] == 'fixed':
            if data['discount_value'] is None:
                errors['discount_value'] = "Discount value is required for fixed-amount coupons."
            if data['discount_percentage'] is not None:
                errors['discount_percentage'] = "Discount percentage should not be set for fixed-amount coupons."

        try:
            data['minimum_purchase_amount'] = float(data['minimum_purchase_amount'])
            if data['minimum_purchase_amount'] < 0:
                errors['minimum_purchase_amount'] = "Minimum purchase amount cannot be negative."
        except ValueError:
            errors['minimum_purchase_amount'] = "Minimum purchase amount must be a valid number."

        try:
            data['max_discount_amount'] = float(data['max_discount_amount'])
            if data['max_discount_amount'] < 0:
                errors['max_discount_amount'] = "Maximum discount amount cannot be negative."
            if data['discount_type'] == 'percentage' and data['max_discount_amount'] <= 0:
                errors['max_discount_amount'] = "Maximum discount amount must be greater than 0 for percentage discounts."
        except ValueError:
            errors['max_discount_amount'] = "Maximum discount amount must be a valid number."

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
                coupon.code = data['code']
                coupon.description = data['description']
                coupon.discount_type = data['discount_type']
                coupon.discount_percentage = data['discount_percentage']
                coupon.discount_value = data['discount_value']
                coupon.minimum_purchase_amount = data['minimum_purchase_amount']
                coupon.max_discount_amount = data['max_discount_amount']
                coupon.valid_from = data['valid_from']
                coupon.valid_until = data['valid_until']
                coupon.usage_limit = data['usage_limit']
                coupon.is_active = data['is_active']
                coupon.save()
                messages.success(request, "Coupon updated successfully!")
                return redirect('coupon')
            except Exception as e:
                messages.error(request, f"Error updating coupon: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        data = {
            'code': coupon.code,
            'description': coupon.description,
            'discount_type': coupon.discount_type,
            'discount_percentage': coupon.discount_percentage,
            'discount_value': coupon.discount_value,
            'minimum_purchase_amount': coupon.minimum_purchase_amount,
            'max_discount_amount': coupon.max_discount_amount,
            'valid_from': coupon.valid_from,
            'valid_until': coupon.valid_until,
            'usage_limit': coupon.usage_limit,
            'is_active': coupon.is_active,
        }

    context = {
        'coupon': coupon,
        'data': data,
        'errors': errors,
    }
    return render(request, 'edit_coupon.html', context)



def delete_coupon(request, id):
    if request.method == 'POST':
        coupon = get_object_or_404(Coupon, id=id)
        try:
            coupon.delete()
            messages.success(request, f"Coupon '{coupon.code}' deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting coupon: {str(e)}")
    else:
        messages.error(request, "Invalid request method. Please use the delete button to remove a coupon.")
    return redirect('coupon')




def available_coupons(request):
    current_datetime = timezone.now()
    
    coupons = Coupon.objects.filter(
        is_active=True,
        valid_until__gt=current_datetime
    ).order_by('-valid_from')
    
    paginator = Paginator(coupons, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj
    }
    return render(request, 'available_coupons.html', context)



@csrf_exempt
@login_required
def apply_coupon(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            coupon_code = data.get('coupon_code', '').strip()
            
            if not coupon_code:
                return JsonResponse({'success': False, 'message': 'Coupon code is required.'}, status=400)

            try:
                coupon = Coupon.objects.get(code=coupon_code)
            except Coupon.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'Invalid coupon code.'}, status=400)

            if not coupon.can_be_used():
                return JsonResponse({
                    'success': False,
                    'message': 'Coupon is not valid or has expired.'
                }, status=400)

            if coupon.usage_limit <= CouponUsage.objects.filter(coupon=coupon).count():
                return JsonResponse({
                    'success': False,
                    'message': 'Coupon has reached its usage limit.'
                }, status=400)

            if CouponUsage.objects.filter(user=request.user, coupon=coupon).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'You have already used this coupon.'
                }, status=400)

            cart = get_object_or_404(Cart, user=request.user)
            subtotal = sum(item.variant.product.price * item.quantity for item in cart.items.all())

            if subtotal < coupon.minimum_purchase_amount:
                return JsonResponse({
                    'success': False,
                    'message': f'Minimum purchase of ₹{coupon.minimum_purchase_amount} required.'
                }, status=400)

            if coupon.discount_type == 'percentage':
                discount = (coupon.discount_percentage / 100) * subtotal
                if coupon.max_discount_amount and discount > coupon.max_discount_amount:
                    discount = coupon.max_discount_amount
            else:
                discount = coupon.discount_value

            shipping = Decimal('40.00') if subtotal < 1000 else Decimal('0.00')
            new_total = subtotal - discount + shipping

            cart.discount_amount = Decimal(discount)
            cart.discounted_total = Decimal(new_total)
            cart.save()

            request.session['coupon_code'] = coupon_code
            request.session.modified = True

            return JsonResponse({
                'success': True,
                'message': 'Coupon applied successfully!',
                'discount': float(discount),
                'new_total': float(new_total)
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error applying coupon: {str(e)}'}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)



@login_required
def remove_coupon(request):
    if request.method == 'POST':
        try:
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
                request.session.modified = True
                return JsonResponse({'success': True, 'message': 'Coupon removed successfully!'})
            return JsonResponse({'success': False, 'message': 'No coupon applied.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error removing coupon: {str(e)}'}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)