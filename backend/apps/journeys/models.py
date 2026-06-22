from django.db import models
from django.utils import timezone
from apps.channels.models import AdChannel


class ConversionPath(models.Model):
    user_id = models.CharField(max_length=200, unique=True)
    converted = models.BooleanField(default=False)
    conversion_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conversion_time = models.DateTimeField(
        default=timezone.now,
        help_text='Timestamp when the conversion actually occurred',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Path {self.id} - user {self.user_id}"

    def get_effective_conversion_time(self):
        """Return conversion_time if set, otherwise fall back to created_at.

        For backward compatibility with existing data that may not have
        conversion_time populated yet.
        """
        return self.conversion_time or self.created_at


class TouchPoint(models.Model):
    path = models.ForeignKey(ConversionPath, on_delete=models.CASCADE, related_name='touchpoints')
    channel = models.ForeignKey(AdChannel, on_delete=models.CASCADE, related_name='touchpoints')
    timestamp = models.DateTimeField()
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"TouchPoint {self.position} on Path {self.path_id}"
