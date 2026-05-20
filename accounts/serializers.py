from rest_framework import serializers
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'role', 'bio', 'phone', 'profile_photo_url',
            'is_email_verified', 'is_active', 'date_joined', 'last_login'
        )
        read_only_fields = ('id', 'email', 'role', 'date_joined', 'last_login', 'is_email_verified')

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_profile_photo_url(self, obj):
        return obj.get_profile_photo_url()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'password', 'password_confirm')

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user
