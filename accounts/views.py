from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from functools import wraps
import uuid

from .models import CustomUser, UserActivity
from .forms import (
    RegistrationForm, CustomLoginForm, OTPLoginForm, OTPVerifyForm,
    ForgotPasswordForm, ResetPasswordForm, ProfileUpdateForm, ChangePasswordForm
)


# ============================================================
# DECORATORS
# ============================================================

def role_required(*roles):
    """Decorator to restrict views by user role"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            if request.user.role not in roles and not request.user.is_superuser:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def log_activity(user, action, request):
    """Log user activity"""
    ip = request.META.get('REMOTE_ADDR', '')
    ua = request.META.get('HTTP_USER_AGENT', '')
    UserActivity.objects.create(user=user, action=action, ip_address=ip, user_agent=ua)


# ============================================================
# AUTH VIEWS
# ============================================================

def register_view(request):
    """User Registration with email verification"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.is_email_verified = False
            user.save()

            # Generate and send email verification token
            token = user.generate_verification_token()
            verification_url = request.build_absolute_uri(
                f'/accounts/verify-email/{token}/'
            )
            send_mail(
                subject='Verify your email - AuthProject',
                message=f'Hi {user.username},\n\nClick to verify your email:\n{verification_url}\n\nThis link is valid for 24 hours.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

            log_activity(user, 'Registered', request)
            messages.success(request, f'Account created! Please check {user.email} to verify your account.')
            return redirect('login')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Email + Password Login"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)

            user = authenticate(request, username=email, password=password)
            if user:
                if not user.is_active:
                    messages.error(request, 'Your account has been deactivated.')
                    return render(request, 'accounts/login.html', {'form': form})

                login(request, user)

                if not remember_me:
                    request.session.set_expiry(0)  # Session expires on browser close

                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                log_activity(user, 'Logged in', request)

                messages.success(request, f'Welcome back, {user.get_short_name()}!')
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid email or password.')
    else:
        form = CustomLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Logout"""
    if request.user.is_authenticated:
        log_activity(request.user, 'Logged out', request)
        logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


def verify_email_view(request, token):
    """Email verification via token link"""
    try:
        user = CustomUser.objects.get(email_verification_token=token)
        user.is_email_verified = True
        user.email_verification_token = None
        user.save(update_fields=['is_email_verified', 'email_verification_token'])
        messages.success(request, 'Email verified successfully! You can now login.')
        log_activity(user, 'Email verified', request)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid or expired verification link.')

    return redirect('login')


def forgot_password_view(request):
    """Send password reset email"""
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                token = user.generate_password_reset_token()
                reset_url = request.build_absolute_uri(
                    f'/accounts/reset-password/{token}/'
                )
                send_mail(
                    subject='Password Reset - AuthProject',
                    message=f'Hi {user.username},\n\nClick to reset your password:\n{reset_url}\n\nThis link expires in 24 hours.\n\nIf you did not request this, please ignore.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except CustomUser.DoesNotExist:
                pass  # Don't reveal if email exists

            # Always show same message for security
            messages.success(request, 'If that email exists, we sent a reset link.')
            return redirect('login')
    else:
        form = ForgotPasswordForm()

    return render(request, 'accounts/forgot_password.html', {'form': form})


def reset_password_view(request, token):
    """Reset password via token"""
    try:
        user = CustomUser.objects.get(password_reset_token=token)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid reset link.')
        return redirect('forgot_password')

    if user.password_reset_expiry and timezone.now() > user.password_reset_expiry:
        messages.error(request, 'This reset link has expired. Please request a new one.')
        return redirect('forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password1'])
            user.password_reset_token = None
            user.password_reset_expiry = None
            user.save()
            messages.success(request, 'Password reset successfully! Please login.')
            log_activity(user, 'Password reset', request)
            return redirect('login')
    else:
        form = ResetPasswordForm()

    return render(request, 'accounts/reset_password.html', {'form': form, 'token': token})


# ============================================================
# OTP LOGIN
# ============================================================

def otp_login_view(request):
    """Request OTP login - Step 1: Enter email"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = OTPLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                otp = user.generate_otp()
                send_mail(
                    subject='Your OTP - AuthProject',
                    message=f'Hi {user.username},\n\nYour OTP is: {otp}\n\nValid for 10 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                request.session['otp_email'] = email
                messages.success(request, 'OTP sent to your email!')
                return redirect('otp_verify')
            except CustomUser.DoesNotExist:
                pass
            messages.success(request, 'If that email exists, OTP was sent.')
    else:
        form = OTPLoginForm()

    return render(request, 'accounts/otp_login.html', {'form': form})


def otp_verify_view(request):
    """Verify OTP - Step 2"""
    email = request.session.get('otp_email')
    if not email:
        return redirect('otp_login')

    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp']
            try:
                user = CustomUser.objects.get(email=email)
                if user.verify_otp(otp_input):
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    del request.session['otp_email']
                    user.otp_secret = ''
                    user.save(update_fields=['otp_secret'])
                    log_activity(user, 'OTP Login', request)
                    messages.success(request, f'Welcome, {user.get_short_name()}!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Invalid or expired OTP.')
            except CustomUser.DoesNotExist:
                messages.error(request, 'User not found.')
    else:
        form = OTPVerifyForm()

    return render(request, 'accounts/otp_verify.html', {'form': form, 'email': email})


# ============================================================
# DASHBOARD & PROFILE
# ============================================================

@login_required
def dashboard_view(request):
    """User Dashboard"""
    user = request.user
    activities = UserActivity.objects.filter(user=user)[:5]
    return render(request, 'accounts/dashboard.html', {
        'user': user,
        'activities': activities,
    })


@login_required
def profile_view(request):
    """View Profile"""
    activities = UserActivity.objects.filter(user=request.user)[:10]
    return render(request, 'accounts/profile.html', {
        'activities': activities
    })


@login_required
def profile_edit_view(request):
    """Edit Profile + Photo Upload"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            log_activity(request.user, 'Profile updated', request)
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def change_password_view(request):
    """Change Password"""
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            user = request.user
            if user.check_password(form.cleaned_data['current_password']):
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, 'Password changed successfully!')
                log_activity(user, 'Password changed', request)
                return redirect('profile')
            else:
                messages.error(request, 'Current password is incorrect.')
    else:
        form = ChangePasswordForm()

    return render(request, 'accounts/change_password.html', {'form': form})


# ============================================================
# ADMIN PANEL (custom, separate from Django admin)
# ============================================================

@login_required
@role_required('admin')
def admin_panel_view(request):
    """Custom Admin Panel - User Management"""
    users = CustomUser.objects.all().order_by('-date_joined')
    total_users = users.count()
    admins = users.filter(role='admin').count()
    sellers = users.filter(role='seller').count()
    verified = users.filter(is_email_verified=True).count()

    return render(request, 'accounts/admin_panel.html', {
        'users': users,
        'stats': {
            'total': total_users,
            'admins': admins,
            'sellers': sellers,
            'verified': verified,
            'regular': total_users - admins - sellers,
        }
    })


@login_required
@role_required('admin')
def admin_user_detail_view(request, user_id):
    """Admin: View/Edit a user"""
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_active':
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User {status}.')
        elif action == 'change_role':
            new_role = request.POST.get('role')
            if new_role in ['admin', 'user', 'seller']:
                user.role = new_role
                user.save(update_fields=['role'])
                messages.success(request, f'Role changed to {new_role}.')
        return redirect('admin_user_detail', user_id=user_id)

    activities = UserActivity.objects.filter(user=user)[:10]
    return render(request, 'accounts/admin_user_detail.html', {
        'target_user': user,
        'activities': activities
    })


@login_required
@role_required('admin')
def admin_delete_user_view(request, user_id):
    """Admin: Delete a user"""
    user = get_object_or_404(CustomUser, id=user_id)
    if user == request.user:
        messages.error(request, 'You cannot delete your own account from admin panel.')
        return redirect('admin_panel')
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted.')
        return redirect('admin_panel')
    return render(request, 'accounts/admin_confirm_delete.html', {'target_user': user})
