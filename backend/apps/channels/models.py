from django.db import models
from django.utils import timezone


DEFAULT_ATTRIBUTION_WINDOW_DAYS = 30


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
    attribution_window_days = models.PositiveIntegerField(
        default=DEFAULT_ATTRIBUTION_WINDOW_DAYS,
        help_text='Number of days before conversion during which a touchpoint can contribute credit',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def is_touchpoint_in_window(self, touchpoint_timestamp, conversion_time):
        """Check if a touchpoint falls within this channel's attribution window.

        Args:
            touchpoint_timestamp: datetime of the touchpoint
            conversion_time: datetime of the conversion

        Returns:
            bool: True if touchpoint is within the attribution window
        """
        if touchpoint_timestamp > conversion_time:
            return False
        delta = conversion_time - touchpoint_timestamp
        return delta.days <= self.attribution_window_days
