import random
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from .models import Address
from checkout.models import Order
from checkout.models import OrderItem
from django.utils import timezone
from django.http import JsonResponse
from .models import Profile
from app1.models import Referral
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import logging

logger = logging.getLogger(__name__)










@login_required
def user_profile(request):
    return render(request, 'my_account.html')


@login_required
def edit_profile(request):
    user = request.user 

    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        try:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('my_profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            return redirect('edit_profile')


    return render(request, 'edit_profile.html', {'user': user})




@login_required
def profile_otp(request):
    return render(request, 'profile_otp_verify.html')



@login_required
def new_email(request):
    if request.method == 'POST':
        new_email = request.POST.get('email')


        if not new_email:
            messages.error(request, 'Please provide a valid email address.')
            return redirect('new_mail')
        

        if User.objects.filter(email=new_email).exists():
            messages.error(request, 'This email is already in use.')
            return redirect('new_mail')
        
        #otp generate

        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        print(f"Your otp is {otp}")

        request.session['otp'] = otp
        request.session['new_email'] = new_email
        request.session.modified = True

        subject = 'Your OTP for Email Verification'
        message = f'Your OTP for verifying your new email is: {otp}'

        try:
            
            
            send_mail(subject, message, settings.EMAIL_HOST_USER, [new_email], fail_silently=False )
            messages.success(request, 'OTP has been sent to your new email address.')
        except Exception as e:
            messages.error(request, f'Failed to send OTP: {str(e)}')
            return redirect('new_mail')
        
        return redirect('newmail_otp_verify')


    return render(request, 'new_email.html')



@login_required
def newmail_otp_verify(request):
    if request.method == 'POST':
        submitted_otp = request.POST.get('otp')
        stored_otp = request.session.get('otp')
        new_email = request.session.get('new_email')
        print(f"Submitted OTP: {submitted_otp}, Stored OTP: {stored_otp}, New Email: {new_email}")


        if not submitted_otp or not stored_otp or not new_email:
            messages.error(request, 'Invalid session data. Please try again.')
            return redirect('edit_profile')
        
        if submitted_otp == stored_otp:

            user = request.user
            user.email = new_email
            user.save()
            print(f"Updated email for user {user.username} to {user.email}")

            update_session_auth_hash(request, user)

            request.session.pop('otp', None)
            request.session.pop('new_email', None)

            messages.success(request, 'Email updated successfully!')
            return redirect('my_profile')
        else:

            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('newmail_otp_verify')

    return render(request, 'newmail_otp_verify.html')



def my_profile(request):
    user = User.objects.get(id=request.user.id)
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':
        if 'profile_photo' in request.FILES:
            profile_photo = request.FILES['profile_photo']
            # Validate file size (max 5MB)
            if profile_photo.size > 5 * 1024 * 1024:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'File size exceeds 5MB limit.'})
                messages.error(request, 'File size exceeds 5MB limit.')
                return redirect('my_profile')
            # Validate file type
            if not profile_photo.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Only JPG, JPEG, PNG, and GIF files are allowed.'})
                messages.error(request, 'Only JPG, JPEG, PNG, and GIF files are allowed.')
                return redirect('my_profile')
            # Delete the old photo if it exists
            if profile.profile_photo:
                profile.profile_photo.delete(save=False)
            profile.profile_photo = profile_photo
            profile.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'profile_photo_url': profile.profile_photo.url})
            messages.success(request, 'Profile photo updated successfully!')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Please select a photo to upload.'})
            messages.error(request, 'Please select a photo to upload.')
        return redirect('my_profile')

    context = {
        'user': user,
        'user_profile': profile,
    }
    return render(request, 'my_profile.html', context)



#change password

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user

        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change_password')

        
        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
            return redirect('change_password')

        if not re.search(r'[A-Z]', new_password):
            messages.error(request, 'New password must contain at least one uppercase letter.')
            return redirect('change_password')

        if not re.search(r'[0-9]', new_password):
            messages.error(request, 'New password must contain at least one number.')
            return redirect('change_password')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            messages.error(request, 'New password must contain at least one special character.')
            return redirect('change_password')

        user.set_password(new_password)
        user.save()

        update_session_auth_hash(request, user)

        messages.success(request, 'Password updated successfully!')
        return redirect('my_profile')

    return render(request, 'change_password.html')




#ADDRESS 

@login_required
def address(request):

    addresses = Address.objects.filter(user=request.user)
    logger.debug(f"Addresses for user {request.user}: {addresses}")
    return render(request, 'address.html', {'addresses':addresses})
  





#ADD ADDRESS

def add_address(request):
    if request.method == 'POST':
        street_address = request.POST.get('street_address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postal_code = request.POST.get('postal_code')
        country = request.POST.get('country')
        phone_number = request.POST.get('phone_number')
        is_default = request.POST.get('is_default') == 'on'

        if not all([street_address, city, state, postal_code, country, phone_number]):
            messages.error(request, 'All fields are required.')
            form_data = {
                'street_address': street_address or '',
                'city': city or '',
                'state': state or '',
                'postal_code': postal_code or '',
                'country': country or '',
                'phone_number': phone_number or '',
                'is_default': is_default,
            }
            return render(request, 'add_address.html', {'form_data': form_data})

        try:
            address = Address(
                user=request.user,
                street_address=street_address,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
                phone_number=phone_number,
                is_default=is_default
            )
            address.save()

            
            if is_default:
                Address.objects.filter(user=request.user, is_default=True).exclude(id=address.id).update(is_default=False)

            messages.success(request, 'Address added successfully.')
            next_page = request.GET.get('next', 'address') 
            if next_page == 'checkout':
                return redirect('checkout')  
            return redirect('address')
        except Exception as e:
            messages.error(request, f'Error adding address: {str(e)}')
            form_data = {
                'street_address': street_address or '',
                'city': city or '',
                'state': state or '',
                'postal_code': postal_code or '',
                'country': country or '',
                'phone_number': phone_number or '',
                'is_default': is_default,
            }
            return render(request, 'add_address.html', {'form_data': form_data})

    return render(request, 'add_address.html', {'form_data': {}})





#EDIT ADDRESS


@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        address.street_address = request.POST.get('street_address')
        address.city = request.POST.get('city')
        address.state = request.POST.get('state')
        address.postal_code = request.POST.get('postal_code')
        address.country = request.POST.get('country')
        address.phone_number = request.POST.get('phone_number')
        if not address.phone_number.isdigit():
            messages.error(request, 'Phone number must contain only digits.')
            return render(request, 'edit_address.html', {'address': address})
        if len(address.phone_number) < 10:
            messages.error(request, "Phone number must be at least 10 digits.")
            return render(request, 'edit_address.html', {'address': address})
        address.save()
        messages.success(request, "Address updated successfully!")
        return redirect('address')
    return render(request, 'edit_address.html', {'address': address})







#DELETE ADDRESS

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address deleted successfully!")
    return redirect('address')




#SET DEFAULT


@login_required
def set_default_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    address.is_default = True
    address.save()
    messages.success(request, "Default address updated successfully!")
    return redirect('address')



@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    orders_per_page = 5 

    paginator = Paginator(orders, orders_per_page)

    page_number = request.GET.get('page')

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        'orders': page_obj,  
        'page_obj': page_obj, 
    }
    return render(request, 'my_orders.html', context)




# refferel




@login_required
def referrals(request):
    # Get the user's referral object
    try:
        referral = request.user.referral
        referral_code = referral.referral_code
    except Referral.DoesNotExist:
        # If the user doesn't have a referral object, create one
        referral = Referral.objects.create(user=request.user)
        referral_code = referral.referral_code

    # Generate the referral link
    base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')  # Replace with your domain in settings.py
    referral_link = f"{base_url}/register?ref={referral_code}"

    # Get users who were referred by this user
    referred_friends = User.objects.filter(referral__referred_by=request.user)

    context = {
        'referral_code': referral_code,
        'referral_link': referral_link,
        'referred_friends': referred_friends,
    }
    return render(request, 'referrals.html', context)
  




