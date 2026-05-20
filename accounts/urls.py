from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<uuid:token>/', views.verify_email_view, name='verify_email'),

    # Password
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/<uuid:token>/', views.reset_password_view, name='reset_password'),

    # OTP Login
    path('otp-login/', views.otp_login_view, name='otp_login'),
    path('otp-verify/', views.otp_verify_view, name='otp_verify'),

    # Profile & Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('change-password/', views.change_password_view, name='change_password'),

    # Admin Panel
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('admin-panel/user/<uuid:user_id>/', views.admin_user_detail_view, name='admin_user_detail'),
    path('admin-panel/user/<uuid:user_id>/delete/', views.admin_delete_user_view, name='admin_delete_user'),
]
