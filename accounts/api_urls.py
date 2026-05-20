from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api_views import (
    RegisterAPIView, LoginAPIView, LogoutAPIView,
    ProfileAPIView, ChangePasswordAPIView, UserListAPIView
)

urlpatterns = [
    # JWT Auth
    path('auth/register/', RegisterAPIView.as_view(), name='api_register'),
    path('auth/login/', LoginAPIView.as_view(), name='api_login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api_logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User
    path('user/profile/', ProfileAPIView.as_view(), name='api_profile'),
    path('user/change-password/', ChangePasswordAPIView.as_view(), name='api_change_password'),

    # Admin only
    path('admin/users/', UserListAPIView.as_view(), name='api_user_list'),
]
