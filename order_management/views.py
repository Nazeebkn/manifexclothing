from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from checkout.models import OrderItem
from django.contrib import messages

from checkout.models import Order
from wallet.models import Wallet,WalletTransaction
from django.core.paginator import Paginator
from django.shortcuts import render
from decimal import Decimal
from django.db.models import Q
from checkout.models import Order
import logging



logger = logging.getLogger(__name__)
def order_management(request):
    search_query = request.GET.get('search', '')
    
    orders = Order.objects.all().order_by('-created_at')
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    logger.info(f"Orders found: {orders.count()}")
    for order in orders:
        logger.info(f"Order {order.id}: Status={order.status}, Display Status={order.get_status_display()}, Items={order.items.count()}")
    
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'order_management.html', context)




@staff_member_required
def order_management_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    order_items_with_total = [
        {
            'item': item,
            'total_price': item.quantity * item.price
        }
        for item in order_items
    ]
    context = {
        'order': order,
        'order_items_with_total': order_items_with_total,
    }
    return render(request, 'order_management_details.html', context)

def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status:
            try:
                if new_status not in dict(order.ORDER_STATUS_CHOICES):
                    messages.error(request, f"Invalid status: {new_status}")
                else:
                    order.status = new_status
                    order.save(update_fields=['status'])
                    messages.success(request, f"Order {order.id} status updated to {order.get_status_display()}.")
            except Exception as e:
                messages.error(request, f"Failed to update order status: {str(e)}")
        else:
            messages.error(request, "No status provided.")
    return redirect('order_management_details', order_id=order.id)


def update_order_item_status(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')



        if new_status:
            try:
                if new_status not in dict(item.ORDER_ITEM_STATUS_CHOICES):
                    messages.error(request, f"Invalid status: {new_status}")
                elif item.can_update_status(new_status):



                    if new_status== 'return':
                        refund_amount = item.price * item.quantity

                        item.status = 'returned'
                        item.save()
                        refund_amount = max(refund_amount, Decimal('0.00'))

                        wallet, created = Wallet.objects.get_or_create(user=item.order.user)
                        wallet.balance += refund_amount
                        wallet.save()

                        WalletTransaction.objects.create(
                        wallet=wallet,
                        order=item.order,
                        amount=refund_amount,
                        transaction_type='credit'
                        )
                    
                    
                    
                    item.status = new_status
                    item.save(update_fields=['status'])
                    item.order.update_order()
                    item.order.save(update_fields=['status'])
                    messages.success(request, f"Item {item.id} status updated to {item.get_status_display()}.")
                else:
                    messages.error(request, f"Cannot update item {item.id} to {new_status} from {item.get_status_display()}.")
            except Exception as e:
                messages.error(request, f"Failed to update item status: {str(e)}")
        else:
            messages.error(request, "No status provided.")
    return redirect('order_management_details', order_id=item.order.id)