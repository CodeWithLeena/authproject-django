from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import CustomUser
from .serializers import UserSerializer, RegisterSerializer


class RegisterAPIView(APIView):
    """POST /api/auth/register/ - Register new user"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Registration successful',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    """POST /api/auth/login/ - Login and get JWT tokens"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Email and password required'}, status=400)

        user = authenticate(request, username=email, password=password)
        if user:
            if not user.is_active:
                return Response({'error': 'Account is deactivated'}, status=403)

            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        return Response({'error': 'Invalid credentials'}, status=401)


class LogoutAPIView(APIView):
    """POST /api/auth/logout/ - Blacklist refresh token"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully'})
        except Exception:
            return Response({'error': 'Invalid token'}, status=400)


class ProfileAPIView(generics.RetrieveUpdateAPIView):
    """GET/PUT /api/user/profile/ - View and update profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordAPIView(APIView):
    """POST /api/user/change-password/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        current = request.data.get('current_password')
        new_pass = request.data.get('new_password')

        if not user.check_password(current):
            return Response({'error': 'Current password is incorrect'}, status=400)
        if len(new_pass) < 8:
            return Response({'error': 'Password must be at least 8 characters'}, status=400)

        user.set_password(new_pass)
        user.save()
        return Response({'message': 'Password changed successfully'})


class UserListAPIView(generics.ListAPIView):
    """GET /api/admin/users/ - Admin only user list"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'admin' and not self.request.user.is_superuser:
            return CustomUser.objects.none()
        return CustomUser.objects.all().order_by('-date_joined')
