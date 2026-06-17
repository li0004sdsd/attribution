from django.db import models
from apps.channels.models import AdChannel


class ConversionPath(models.Model):
    user_id = models.CharField(max_length=200)
    converted = models.BooleanField(default=False)
    conversion_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Path {self.id} - user {self.user_id}"


class TouchPoint(models.Model):
    path = models.ForeignKey(ConversionPath, on_delete=models.CASCADE, related_name='touchpoints')
    channel = models.ForeignKey(AdChannel, on_delete=models.CASCADE, related_name='touchpoints')
    timestamp = models.DateTimeField()
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"TouchPoint {self.position} on Path {self.path_id}"
