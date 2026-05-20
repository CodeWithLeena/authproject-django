from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid
import random
import string


class CustomUserManager(BaseUserManager):
    """Custom manager for CustomUser"""

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        if not username:
            raise ValueError('Username is required')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_email_verified', True)
        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model with:
    - Email as username
    - Role-based access (admin/user/seller)
    - Email verification
    - OTP support
    - Profile photo
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        USER = 'user', 'User'
        SELLER = 'seller', 'Seller'

    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)

    # Personal info
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    profile_photo = models.ImageField(
        upload_to='profile_pics/',
        null=True,
        blank=True,
        default=None
    )

    # Role
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER
    )

    # Account status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Email verification & password reset tokens
    email_verification_token = models.UUIDField(null=True, blank=True)
    password_reset_token = models.UUIDField(null=True, blank=True)
    password_reset_expiry = models.DateTimeField(null=True, blank=True)

    # OTP fields
    otp_secret = models.CharField(max_length=32, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.email} ({self.role})"

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def get_short_name(self):
        return self.first_name or self.username

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER

    def generate_otp(self):
        """Generate 6-digit OTP"""
        otp = ''.join(random.choices(string.digits, k=6))
        self.otp_secret = otp
        self.otp_created_at = timezone.now()
        self.save(update_fields=['otp_secret', 'otp_created_at'])
        return otp

    def verify_otp(self, otp_input):
        """Verify OTP (valid for 10 minutes)"""
        if not self.otp_secret or not self.otp_created_at:
            return False
        expiry = self.otp_created_at + timezone.timedelta(minutes=10)
        if timezone.now() > expiry:
            return False
        return self.otp_secret == otp_input

    def generate_verification_token(self):
        token = uuid.uuid4()
        self.email_verification_token = token
        self.save(update_fields=['email_verification_token'])
        return token

    def generate_password_reset_token(self):
        token = uuid.uuid4()
        self.password_reset_token = token
        self.password_reset_expiry = timezone.now() + timezone.timedelta(hours=24)
        self.save(update_fields=['password_reset_token', 'password_reset_expiry'])
        return token

    def get_profile_photo_url(self):
        if self.profile_photo:
            return self.profile_photo.url
        return '/static/images/default_avatar.png'


class UserActivity(models.Model):
    """Track user login activity"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'User Activities'

    def __str__(self):
        return f"{self.user.email} - {self.action} at {self.timestamp}"
