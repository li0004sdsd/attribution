from django.contrib.auth.models import User
from django.db import models


ROLE_ADMIN = 'admin'
ROLE_OPERATOR = 'operator'
ROLE_USER = 'user'

ROLE_CHOICES = [
    (ROLE_ADMIN, 'Administrator'),
    (ROLE_OPERATOR, 'Operator'),
    (ROLE_USER, 'Regular User'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
    allowed_models = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f"{self.user.username} - {self.role}"


def get_user_role(user):
    if user.is_superuser:
        return ROLE_ADMIN
    try:
        return user.profile.role
    except UserProfile.DoesNotExist:
        return ROLE_USER


def get_allowed_models(user):
    if user.is_superuser:
        return None
    try:
        profile = user.profile
        if profile.role == ROLE_ADMIN:
            return None
        if profile.role == ROLE_OPERATOR:
            return list(profile.allowed_models or [])
        return []
    except UserProfile.DoesNotExist:
        return []


__all__ = [
    'User', 'UserProfile',
    'ROLE_ADMIN', 'ROLE_OPERATOR', 'ROLE_USER', 'ROLE_CHOICES',
    'get_user_role', 'get_allowed_models',
]
