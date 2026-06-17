from django.db import models


class AdChannel(models.Model):
    PLATFORM_CHOICES = [
        ('google', 'Google Ads'),
        ('facebook', 'Facebook Ads'),
        ('twitter', 'Twitter Ads'),
        ('linkedin', 'LinkedIn Ads'),
        ('tiktok', 'TikTok Ads'),
        ('email', 'Email'),
        ('organic', 'Organic'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, default='other')
    cost_per_click = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
