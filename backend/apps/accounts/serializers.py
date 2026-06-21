from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile, get_user_role, get_allowed_models


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        write_only=True,
        required=False,
        default='user',
    )
    allowed_models = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        default=[],
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'role', 'allowed_models')

    def create(self, validated_data):
        role = validated_data.pop('role', 'user')
        allowed_models = validated_data.pop('allowed_models', [])
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.allowed_models = list(allowed_models or [])
        profile.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    allowed_models = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'allowed_models')

    def get_role(self, obj):
        return get_user_role(obj)

    def get_allowed_models(self, obj):
        result = get_allowed_models(obj)
        if result is None:
            return ['first_touch', 'last_touch', 'linear', 'custom_weight']
        return result
