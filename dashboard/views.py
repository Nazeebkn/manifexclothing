from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from coupon.models import CouponUsage
from checkout.models import Order
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from io import BytesIO
import logging
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.db.models.functions import TruncYear, TruncMonth, TruncWeek
from checkout.models import Order, OrderItem
from django.utils import timezone
from datetime import timedelta
from products.models import Product, ProductVariant, Size
from categories.models import categories
from checkout.models import Order, OrderItem
from django.contrib.auth.models import User

def admin_dashboard(request):
    total_customers = User.objects.count()
    total_revenue = Order.objects.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_orders = Order.objects.count()
    total_products = Product.objects.count()

    recent_orders = Order.objects.all().order_by('-created_at')[:5]
    status_mapping = {
        'completed': 'delivered',
        'canceled': 'canceled',
        'returned': 'returned',
        'processing': 'processing',
        'pending': 'pending'
    }
    recent_orders = [
        {
            'id': order.id,
            'user': order.user,
            'created_at': order.created_at,
            'total_price': order.total_price,
            'status': status_mapping.get(order.status, order.status)
        }
        for order in recent_orders
    ]

    top_products = (
        OrderItem.objects.filter(order__status='completed')
        .values('size__variant__product__name')
        .annotate(total_sold=Sum('quantity'), sales=Sum('price'))
        .order_by('-total_sold')[:5]
    )
    top_categories = (
        OrderItem.objects.filter(order__status='completed')
        .values('size__variant__product__category__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:10]
    )

    context = {
        'total_customers': total_customers,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_products': total_products,
        'recent_orders': recent_orders,
        'top_products': [
            {'name': item['size__variant__product__name'], 
             'total_sold': item['total_sold'],
             'sales': float(item['sales'])}
            for item in top_products
        ],
        'top_categories': [
            {'name': item['size__variant__product__category__name'], 
             'total_sold': item['total_sold']}
            for item in top_categories
        ],
    }
    return render(request, 'dashboard.html', context)

def dashboard_data(request):
    time_period = request.GET.get('time_period', 'all')
    order_status = request.GET.get('order_status', 'all')

    # Base queryset for orders
    orders = Order.objects.all()
    if order_status != 'all':
        orders = orders.filter(status=order_status)

    # Define the current date and time (June 05, 2025, as per the system)
    now = timezone.make_aware(datetime(2025, 6, 5, 23, 59, 59))  # End of June 05, 2025

    # Filter orders based on time period
    if time_period == 'today':
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_of_day, created_at__lte=now)
    elif time_period == 'yesterday':
        start_of_yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_yesterday = start_of_yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        orders = orders.filter(created_at__gte=start_of_yesterday, created_at__lte=end_of_yesterday)
    elif time_period == 'last_7_days':
        start_of_period = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        orders = orders.filter(created_at__gte=start_of_period, created_at__lte=now)
    elif time_period == 'weekly':
        orders = orders.filter(created_at__gte=now - timedelta(days=7))
    elif time_period == 'monthly':
        orders = orders.filter(created_at__gte=now - timedelta(days=30))
    elif time_period == 'yearly':
        orders = orders.filter(created_at__gte=now - timedelta(days=365))

    # Overview Data
    total_customers = User.objects.count()
    total_revenue = orders.filter(status='completed').aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_orders = orders.count()
    total_products = Product.objects.count()

    # Recent Orders
    recent_orders = orders.order_by('-created_at')[:5]
    status_mapping = {
        'completed': 'delivered',
        'canceled': 'canceled',
        'returned': 'returned',
        'processing': 'processing',
        'pending': 'pending'
    }
    recent_orders_data = [
        {
            'id': order.id,
            'user': order.user.username,
            'created_at': order.created_at.strftime('%d/%m/%Y'),
            'total_price': float(order.total_price),
            'status': status_mapping.get(order.status, order.status)
        }
        for order in recent_orders
    ]

    # Top Selling Products
    top_products = (
        OrderItem.objects.filter(
            order__in=orders,
            order__status='completed',
            size__variant__product__isnull=False
        )
        .values('size__variant__product__name')
        .annotate(total_sold=Sum('quantity'), sales=Sum('price'))
        .order_by('-total_sold')[:5]
    )
    top_products_data = [
        {
            'name': item['size__variant__product__name'],
            'total_sold': item['total_sold'],
            'sales': float(item['sales'])
        }
        for item in top_products
    ]

    # Top Categories
    top_categories = (
        OrderItem.objects.filter(
            order__in=orders,
            order__status='completed',
            size__variant__product__category__isnull=False
        )
        .values('size__variant__product__category__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:10]
    )
    top_categories_data = [
        {
            'name': item['size__variant__product__category__name'],
            'total_sold': item['total_sold']
        }
        for item in top_categories
    ]

    return JsonResponse({
        'total_customers': total_customers,
        'total_revenue': float(total_revenue),
        'total_orders': total_orders,
        'total_products': total_products,
        'recent_orders': recent_orders_data,
        'top_products': top_products_data,
        'top_categories': top_categories_data,
    })


logger = logging.getLogger(__name__)

def is_superuser(user):
    return user.is_superuser



@user_passes_test(is_superuser)
def sales_report(request):
    filter_type = request.GET.get('filter_type', 'daily')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    today = timezone.now().date()
    no_sales_message = ""

    # Define date ranges based on filter type
    if filter_type == 'daily':
        start = today
        end = today
        period_label = "Daily"
    elif filter_type == 'weekly':
        start = today - timedelta(days=today.weekday())  # Start of the week (Monday)
        end = start + timedelta(days=6)  # End of the week (Sunday)
        period_label = "Weekly"
    elif filter_type == 'yearly':
        start = today.replace(month=1, day=1)  # Start of the year
        end = today.replace(month=12, day=31)  # End of the year
        period_label = "Yearly"
    else:  # Custom filter
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else today - timedelta(days=30)
            end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else today
            period_label = "Custom"
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid date format: start_date={start_date}, end_date={end_date}, error={str(e)}")
            start = today - timedelta(days=30)
            end = today
            period_label = "Custom (Default: Last 30 Days)"

    # Ensure start date is not after end date
    if start > end:
        start, end = end, start

    # Convert to timezone-aware datetimes
    start_dt = timezone.make_aware(datetime.combine(start, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end, datetime.max.time()))
    logger.info(f"Sales report filter: {filter_type}, start: {start_dt}, end: {end_dt}")

    # Filter orders within the date range
    orders = Order.objects.filter(
        created_at__gte=start_dt,
        created_at__lte=end_dt
    ).order_by('-created_at')  # Order by most recent

    # Calculate summary metrics
    total_orders = orders.count()
    total_amount = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_discount = orders.aggregate(Sum('discount_coupon_amount'))['discount_coupon_amount__sum'] or 0

    # Check for no sales and set message
    if total_orders == 0:
        no_sales_message = f"No sales recorded for the selected {period_label.lower()} period ({start} to {end})."

    # Filter coupon usage within the date range
    coupon_usage = CouponUsage.objects.filter(
        used_at__gte=start_dt,
        used_at__lte=end_dt
    ).values('coupon__code').annotate(
        count=Count('id')
    )

    # Handle download requests
    if request.GET.get('download') == 'pdf':
        logger.info(f"Generating PDF sales report for {filter_type} from {start} to {end}")
        return generate_pdf_report(orders, total_orders, total_amount, total_discount, coupon_usage, start, end, filter_type)
    elif request.GET.get('download') == 'excel':
        logger.info(f"Generating Excel sales report for {filter_type} from {start} to {end}")
        return generate_excel_report(orders, total_orders, total_amount, total_discount, coupon_usage, start, end, filter_type)

    context = {
        'orders': orders,
        'total_orders': total_orders,
        'total_amount': total_amount,
        'total_discount': total_discount,
        'coupon_usage': coupon_usage,
        'start_date': start,
        'end_date': end,
        'filter_type': filter_type,
        'no_sales_message': no_sales_message,
        'period_label': period_label,
    }
    return render(request, 'sales_report.html', context)





def generate_pdf_report(orders, total_orders, total_amount, total_discount, coupon_usage, start, end, filter_type):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(name='ReportTitle', fontName='Helvetica-Bold', fontSize=16, alignment=1))

  

    elements.append(Paragraph(f"Sales Report ({filter_type.capitalize()})", styles['ReportTitle']))
    elements.append(Paragraph(f"Date Range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 0.2 * inch))

    summary_data = [
        ['Summary', 'Value'],
        ['Total Orders', str(total_orders)],
        ['Total Amount', f"Rs:{total_amount:.2f}"],
        ['Total Discount', f"Rs:{total_discount:.2f}"]
    ]
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f7fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2 * inch))

    if coupon_usage:
        coupon_data = [['Coupon Code', 'Times Used']]
        for coupon in coupon_usage:
            coupon_data.append([
                coupon['coupon__code'],
                str(coupon['count'])
            ])
        coupon_table = Table(coupon_data)
        coupon_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f7fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(Paragraph("Coupon Usage", styles['Normal']))
        elements.append(coupon_table)
        elements.append(Spacer(1, 0.2 * inch))

    order_data = [['Order ID', 'Date', 'Subtotal', 'Discount', 'Final Amount']]
    for order in orders:
        order_data.append([
            order.id,
            order.created_at.strftime('%Y-%m-%d'),
            f"Rs:{order.total_price:.2f}",
            f"Rs:{order.discount_coupon_amount:.2f}",
            f"Rs:{(order.total_price - order.discount_coupon_amount):.2f}"
        ])
    order_table = Table(order_data)
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f7fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(Paragraph("Order Details", styles['Normal']))
    elements.append(order_table)

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sales_report_{filter_type}_{start}_{end}.pdf"'
    response.write(buffer.read())
    buffer.close()
    return response

def generate_excel_report(orders, total_orders, total_amount, total_discount, coupon_usage, start, end, filter_type):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales Report"

    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="f5f7fa", end_color="f5f7fa", fill_type="solid")
    align_center = Alignment(horizontal="center")

    ws.append([f"Sales Report ({filter_type.capitalize()})"])
    ws.append([f"Date Range: {start} to {end}"])
    ws.append([])
    ws.append(["Summary", "Value"])
    ws.append(["Total Orders", total_orders])
    ws.append(["Total Amount", f"Rs:{total_amount:.2f}"])
    ws.append(["Total Discount", f"Rs:{total_discount:.2f}"])
    ws.append([])

    if coupon_usage:
        ws.append(["Coupon Usage"])
        ws.append(["Coupon Code", "Times Used"])
        for coupon in coupon_usage:
            ws.append([
                coupon['coupon__code'],
                coupon['count']
            ])
        ws.append([])

    ws.append(["Order Details"])
    ws.append(["Order ID", "Date", "Subtotal", "Discount", "Final Amount"])
    for order in orders:
        ws.append([
            order.id,
            order.created_at.strftime('%Y-%m-%d'),
            f"Rs:{order.total_price:.2f}",
            f"Rs:{order.discount_coupon_amount:.2f}",
            f"Rs:{(order.total_price - order.discount_coupon_amount):.2f}"
        ])

    for row in ws[1:ws.max_row]:
        for cell in row:
            if cell.row in [1, 4, 9, 11]:
                cell.font = header_font
                cell.fill = header_fill
            cell.alignment = align_center

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = max_length + 2
        ws.column_dimensions[column].width = adjusted_width

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="sales_report_{filter_type}_{start}_{end}.xlsx"'
    response.write(buffer.read())
    buffer.close()
    return response