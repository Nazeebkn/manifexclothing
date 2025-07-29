from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render
from .models import Wallet, WalletTransaction
import logging
from django.shortcuts import render, get_object_or_404
from checkout.models import Order
from django.contrib.auth.models import User
from django.urls import reverse

logger = logging.getLogger(__name__)

@login_required
def wallet(request):
    user = request.user

    wallet, created = Wallet.objects.get_or_create(user=user, defaults={'balance': 0.00})
    logger.debug(f"Wallet for user {user.id}: balance={wallet.balance}, created={created}")

    wallet_balance = wallet.balance

    filter_type = request.GET.get('filter', 'all')
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
    if filter_type == 'credit':
        transactions = transactions.filter(transaction_type='credit')
    elif filter_type == 'debit':
        transactions = transactions.filter(transaction_type='debit')

    paginator = Paginator(transactions, 10)
    page = request.GET.get('page', 1)
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    try:
        user_profile = user.userprofile
    except AttributeError:
        user_profile = None
        logger.warning(f"No UserProfile for user {user.id}")

    context = {
        'wallet_balance': wallet_balance,
        'transactions': transactions,
        'filter_type': filter_type,
        'user_profile': user_profile,
        'user': user,
    }

    return render(request, 'wallet.html', context)




@login_required
def wallet_management(request):
    """
    Admin view to display a list of all wallet transactions.
    """
    transactions = WalletTransaction.objects.all().order_by('-created_at')

    paginator = Paginator(transactions, 10)
    page = request.GET.get('page', 1)
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    context = {
        'transactions': transactions,
    }
    return render(request, 'wallet_management.html', context)


 

@login_required
def wallet_transaction_detail(request, transaction_id):
    transaction = get_object_or_404(WalletTransaction, transaction_id=transaction_id)
    user = transaction.wallet.user

    source = "Unknown"
    order_link = None

    if transaction.order:
        print(f"Order ID: {transaction.order.id}, Status: {transaction.order.status}")
        if transaction.order.status == 'returned':
            source = f"Order Returned (Order ID: {transaction.order.id})"
            order_link = reverse('order_management_details', args=[transaction.order.id])
            print(f"Order link set to: {order_link}")
        elif transaction.description and 'canceled item' in transaction.description.lower():

            source = f"Item Cancellation (Order ID: {transaction.order.id})"
            order_link = reverse('order_management_details', args=[transaction.order.id])
            print(f"Identified as item cancellation refund")
        else:
            source = f"Order (Order ID: {transaction.order.id}, Status: {transaction.order.status.capitalize()})"
            print(f"Order status '{transaction.order.status}' does not match 'returned' or 'canceled'")
    elif transaction.transaction_type == 'credit' and not transaction.order:
        source = "Referral"
        print(f"Transaction identified as Referral (ID: {transaction.transaction_id})")
    else:
        source = "Unknown"
        print(f"No order or referral identified for transaction ID: {transaction.transaction_id}")

    context = {
        'transaction': transaction,
        'user': user,
        'source': source,
        'order_link': order_link,
    }
    return render(request, 'wallet_transaction_detail.html', context)