from django.urls import path
from . import views


urlpatterns = [
    path('sales_report/',views.sales_report,name='sales_report'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard_data/', views.dashboard_data, name='dashboard_data'),
]
