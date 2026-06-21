from django.db import models
from apps.channels.models import AdChannel


class AttributionResult(models.Model):
    MODEL_CHOICES = [
        ('first_touch', 'First Touch'),
        ('last_touch', 'Last Touch'),
        ('linear', 'Linear'),
        ('custom_weight', 'Custom Weight'),
    ]

    model_type = models.CharField(max_length=50, choices=MODEL_CHOICES)
    channel = models.ForeignKey(AdChannel, on_delete=models.CASCADE, related_name='attribution_results')
    credit = models.DecimalField(max_digits=14, decimal_places=4)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-calculated_at', '-credit']

    def __str__(self):
        return f"{self.model_type} - {self.channel.name}: {self.credit}"
