from .import views
from django.urls import path,include
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    path('',views.index,name='index'),
    path('login/',views.login_user,name='login'),
    path('register/',views.register,name='register'),
    path('otp/',views.otp,name='otp'),
    path('generate_otp/',views.generate_otp,name='generate_otp'),
    path('send_otp_email/',views.send_otp_email,name='send_otp_email'),
    path('validate_password/',views.validate_password,name='validate_password'),
    path('verify_otp/',views.verify_otp,name='verify_otp'),   
    path('resend_otp/',views.resend_otp,name='resend_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:email>/', views.reset_password, name='reset_password'),
    path('logout/', LogoutView.as_view(next_page='index'), name='logout'),
    path('auth/', include('social_django.urls', namespace='social')),
    path('password_otp',views.password_verify_otp,name="password_otp"),


    

    




] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
