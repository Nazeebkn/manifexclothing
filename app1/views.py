from django.shortcuts import render, redirect, HttpResponse, HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
import re
import secrets
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone as django_timezone   
from datetime import timezone as datetime_timezone 
from django.http import JsonResponse
from .models import OTP
import random
from django.conf import settings
import pytz
from datetime import timezone
from categories.models import categories
from products.models import Product,ProductVariant
from .models import Referral
from wallet.models import Wallet, WalletTransaction
from django.views.decorators.cache import never_cache






# Generate 4-digit OTP

# @never_cache
# def generate_otp():
#     otp = random.randint(0, 9999)
#     return str(otp).zfill(4)

# Send OTP to email
 
def send_otp_email(email, otp):
    subject = "Your OTP Code"
    message = f"Your OTP Code is: {otp}"
    print(f"your OTP is {otp}")
    try:
        send_mail(subject, message, "your_gmail.com", [email])
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Password validation
def validate_password(password):
    if password is None:
        return False, "Password cannot be empty."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""


def register(request):
   

    form_data = {}
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        referral_code = request.POST.get('referral_code', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        terms = request.POST.get('check2', False)

        form_data = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'referral_code': referral_code,
        }

        # Validation

        
        errors = {}
        if not username or not re.match(r'^(?=.*[A-Za-z])[A-Za-z0-9\s]{3,}$', username):

            errors['username'] = " must be at least 3 characters and can contain only letters, numbers, and space."
        elif User.objects.filter(username=username).exists():
            errors['username'] = "Username already exists. Please choose a different one."
        
        if not email:
            errors['email'] = "Email is required."
        elif User.objects.filter(email=email).exists():
            errors['email'] = "Email is already registered. Please use a different email."
        
        if not password or not confirm_password:
            errors['password'] = "Password and confirmation are required."
        elif password != confirm_password:
            errors['password'] = "Passwords do not match."
        else:
            is_valid, error_message = validate_password(password)
            if not is_valid:
                errors['password'] = error_message

        if errors:
            for error in errors.values():
                messages.error(request, error)
            return render(request, 'register.html', {'form_data': form_data})
        




        # Validate referral code
        referred_by = None
        if referral_code:
            try:
                referral = Referral.objects.get(referral_code=referral_code)
                referred_by = referral.user
            except Referral.DoesNotExist:
                messages.error(request, "Invalid referral code.")
                return render(request, 'register.html')
        



        
        print(f"Your sending OTP is {otp}")

        # otp = generate_otp()   
        expires_at = django_timezone.now() + timedelta(minutes=1)

        request.session['otp'] = otp
        request.session['otp_expires_at'] = int(expires_at.timestamp())
        request.session['username'] = username
        request.session['email'] = email
        request.session['password'] = password
        request.session['first_name'] = first_name
        request.session['last_name'] = last_name
        request.session['referral_code'] = referral_code

        if not send_otp_email(email, otp):
            messages.error(request, "Failed to send OTP email. Please try again.")
            return render(request, 'register.html', {'form_data': form_data})

        return redirect('verify_otp')

    return render(request, 'register.html', {'form_data': form_data})



@never_cache
def verify_otp(request):
    email = request.session.get('email')
    otp_expires_at = request.session.get('otp_expires_at')

    if request.method == 'POST':
        otp1 = request.POST.get('otp_1')
        otp2 = request.POST.get('otp_2')
        otp3 = request.POST.get('otp_3')
        otp4 = request.POST.get('otp_4')
        entered_otp = otp1 + otp2 + otp3 + otp4
        
        otp = request.session.get('otp')

        if not otp:
            return render(request, 'otp.html', {'error': 'OTP not found.', 'email': email, 'otp_expires_at': otp_expires_at})

        try:
            otp_expires_at_dt = datetime.fromtimestamp(otp_expires_at, tz=datetime_timezone.utc)
        except ValueError:
            return render(request, 'otp.html', {'error': 'Invalid OTP expiration format.', 'email': email, 'otp_expires_at': otp_expires_at})

        if django_timezone.now() > otp_expires_at_dt:
            return render(request, 'otp.html', {'error': 'OTP has expired.', 'email': email, 'otp_expires_at': otp_expires_at})

        if str(otp) == entered_otp:
            username = request.session['username']
            password = request.session['password']
            first_name = request.session['first_name']
            last_name = request.session['last_name']
            referral_code = request.session.get('referral_code')

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            Referral.objects.create(user=user)

            wallet, _ = Wallet.objects.get_or_create(user=user)

            if referral_code:
                referral = Referral.objects.get(referral_code=referral_code)
                referred_by = referral.user
                Referral.objects.filter(user=user).update(referred_by=referred_by)
                
                wallet.balance += 50
                wallet.save()
                WalletTransaction.objects.create(
                    wallet=wallet,
                    amount=50,
                    transaction_type='credit',
                    description='Referral bonus for new user'
                )

                referred_wallet, _ = Wallet.objects.get_or_create(user=referred_by)
                referred_wallet.balance += 100
                referred_wallet.save()
                WalletTransaction.objects.create(
                    wallet=referred_wallet,
                    amount=100,
                    transaction_type='credit',
                    description='Referral bonus for referring user'
                )

            request.session.clear()
            messages.success(request, 'Signup Successful')
            return redirect('login')
        
        else:
            return render(request, 'otp.html', {'error': 'Invalid OTP. Please try again.', 'email': email, 'otp_expires_at': otp_expires_at})

    return render(request, 'otp.html', {'email': email, 'otp_expires_at': otp_expires_at})

# reset password

def reset_password(request, email):
    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'reset_password.html')

        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successful!')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'User not found!')
            return render(request, 'reset_password.html')

    return render(request, 'reset_password.html', {'email': email})

"""
RESEND OTP
"""

def resend_otp(request):
    
        otp = request.session.get('otp')
        otp_expires_at = request.session.get('otp_expires_at')

            
        new_otp = random.randint(0, 9999)
        # new_otp = generate_otp()
        print(new_otp)
        expires_at = django_timezone.now() + timedelta(minutes=1)
        request.session['otp'] = new_otp
        request.session['otp_expires_at'] = int(expires_at.timestamp())  

        if send_otp_email(request.session['email'], new_otp):
            return redirect('verify_otp')
        else:
            return JsonResponse({'success': False, 'message': 'Failed to send OTP. Please try again.'})
    

@never_cache
def login_user(request):

    if request.method == 'POST':
        email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        remember_me = request.POST.get('remember_me') == 'on'
        print(email,password)


        if not email or not password:
            messages.error(request, "Email and password are required.")
            return render(request, 'login.html', {'email': email})


        user = authenticate(request, username=email, password=password)
        if user is None:

            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
                
            except User.DoesNotExist as e:
                print(str(e))

                user = None

        if user is not None:
            login(request, user)
           
            if not remember_me:
                request.session.set_expiry(0) 
            return redirect('index')
        else:
            messages.error(request, "Invalid email or password.")
            return render(request, 'login.html', {'email': email})

    return render(request, 'login.html')            
        

def index(request):
    new_arrivals = Product.objects.filter(is_active=True)
    Categories = categories.objects.filter(is_listed=True)

    products = (
        ProductVariant.objects.filter(product__is_active=True)
        .select_related("product")
        .order_by('-product__id')
        .distinct('product__id')
    )
    
    product_variants = []
    for product in new_arrivals:
        default_variant = product.variants.all().first() 
        product_variants.append((Product, default_variant))


    return render(request, 'index.html', {
        'new_arrivals': products,
        'categories': Categories
    })



def otp(request):
    return render(request,'otp.html')



def logout_view(request):
    logout(request)
    return redirect('index')  


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        
        if not email:
            messages.error(request, 'Enter valid email !')
            return render(request, 'forgot_password.html')
        

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            messages.error(request, 'Account does not exist.')
            return render(request, 'forgot_password.html')

    
        otp = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        request.session['otp']=otp
        print(f"Your OTP is {otp}")
        expires_at = django_timezone.now() + timedelta(minutes=1)

        request.session['otp_expires_at'] = int(expires_at.timestamp())
        request.session['email']=email
        subject = 'Your Password Reset OTP'
        message = f'Your OTP: {otp}. OTP valid for 10 minutes.'
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [email]

        try:
            send_mail(subject, message, from_email, recipient_list)
            messages.success(request, 'Check your email for the OTP.')
            return render(request,'verify_otp.html') 
        except Exception as e:
            print(f"Error sending email: {e}")
            messages.error(request, '"Unable to send OTP". Try again.')
            return render(request, 'forgot_password.html')

    return render(request, 'forgot_password.html')


def password_verify_otp(request):
    if request.method == "POST":
        
        input_otp = request.POST.get("otp")      
        email = request.session.get('email')
        otp = request.session.get('otp')
        otp_expires_at = request.session.get('otp_expires_at')

        if not email or not otp:
            messages.error(request, 'Didn t receive the OTP or email. Try again.')
            return render(request, 'verify_otp.html', {'email': email})

        try:
            otp_expires_at = datetime.fromtimestamp(otp_expires_at, tz=pytz.UTC)
        except ValueError:
            messages.error(request, 'OTP expiry format is incorrect.')
            return render(request, 'verify_otp.html', {'email': email})

        if django_timezone.now() > otp_expires_at:
            messages.error(request, 'OTP expire aayi.')
            return render(request, 'verify_otp.html', {'email': email})

        if str(otp) == input_otp:
            return redirect('reset_password', email=email)
        else:
            messages.error(request, 'Invalid OTP. Try again.')
            return render(request, 'verify_otp.html', {'email': email})

    email = request.session.get('email')
    return render(request, 'verify_otp.html', {'email': email})



