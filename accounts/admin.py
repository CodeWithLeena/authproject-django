from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, UserActivity


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'role_badge', 'is_email_verified', 'is_active', 'date_joined')
    list_filter = ('role', 'is_email_verified', 'is_active', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login', 'id')

    fieldsets = (
        ('Account Info', {'fields': ('id', 'email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'bio', 'phone', 'profile_photo')}),
        ('Role & Status', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_email_verified')}),
        ('Permissions', {'fields': ('groups', 'user_permissions'), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('date_joined', 'last_login')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'role', 'password1', 'password2'),
        }),
    )

    def role_badge(self, obj):
        colors = {
            'admin': '#dc2626',
            'seller': '#d97706',
            'user': '#2563eb',
        }
        color = colors.get(obj.role, '#6b7280')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{}</span>',
            color, obj.role.upper()
        )
    role_badge.short_description = 'Role'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    list_filter = ('action',)
    search_fields = ('user__email', 'action', 'ip_address')
    readonly_fields = ('user', 'action', 'ip_address', 'user_agent', 'timestamp')
    ordering = ('-timestamp',)


# Customize admin site
admin.site.site_header = '🔐 AuthProject Admin'
admin.site.site_title = 'AuthProject'
admin.site.index_title = 'Dashboard'
