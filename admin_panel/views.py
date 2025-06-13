from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test


def is_admin(user):
    return user.is_superuser

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or not an admin.')
    return render(request, 'admin_login.html')

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    search_query = request.GET.get('search', '')
    if search_query:
        users = User.objects.filter(
            username__icontains=search_query
        ) | User.objects.filter(
            email__icontains=search_query
        )
    else:
        users = User.objects.all()
    users = users.order_by('username')  
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def block_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        if user.is_superuser:
            messages.error(request, "Cannot block an admin user.")
        else:
            user.is_active = False
            user.save()
            messages.success(request, f"User {user.username} has been blocked.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")
    return redirect('admin_dashboard')

@login_required
@user_passes_test(is_admin)
def unblock_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        messages.success(request, f"User {user.username} has been unblocked.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")
    return redirect('admin_dashboard')

@login_required
@user_passes_test(is_admin)
def admin_logout(request):
    logout(request)
    return redirect('admin_login')


