from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_authenticated and user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    return render(request, 'dashboard.html')

@login_required
@user_passes_test(is_admin)
def user_management(request):
    search_query = request.GET.get('search', '')
    users = User.objects.filter(is_staff=False).order_by('-date_joined')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | Q(email__icontains=search_query)
        )
    logger.info(f"Users found: {users.count()}, Search query: {search_query}")
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'user_management.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })

@login_required
@user_passes_test(is_admin)
@never_cache
def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    logger.info(f"Block user request for {user.username} (ID: {user_id})")
    if request.method == 'POST':
        if user.is_active:
            user.is_active = False
            user.save()
            messages.success(request, f'{user.username} has been blocked.')
            logger.info(f"User {user.username} blocked successfully")
            return redirect('user_management')
        else:
            messages.warning(request, f'{user.username} is already blocked.')
            logger.warning(f"Attempt to block already blocked user {user.username}")
            return redirect('user_management')
    return render(request, 'confirm_block.html', {'user': user})





@login_required
@never_cache
def unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    logger.info(f"Unblock user request for {user.username} (ID: {user_id})")
    if request.method == 'POST':
        if not user.is_active:
            user.is_active = True
            user.save()
            messages.success(request, f'{user.username} has been unblocked.')
            logger.info(f"User {user.username} unblocked successfully")
            return redirect('user_management')
        else:
            messages.warning(request, f'{user.username} is already active.')
            logger.warning(f"Attempt to unblock already active user {user.username}")
            return redirect('user_management')
    return render(request, 'confirm_unblock.html', {'user': user})