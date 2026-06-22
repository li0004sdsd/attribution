import hashlib
import json
from django.db import models
from django.contrib.auth.models import User
from apps.channels.models import AdChannel


class AttributionTask(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, '待执行'),
        (STATUS_RUNNING, '执行中'),
        (STATUS_SUCCESS, '成功'),
        (STATUS_FAILED, '失败'),
    ]

    MODEL_CHOICES = [
        ('first_touch', 'First Touch'),
        ('last_touch', 'Last Touch'),
        ('linear', 'Linear'),
        ('custom_weight', 'Custom Weight'),
    ]

    model_type = models.CharField(max_length=50, choices=MODEL_CHOICES)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attribution_tasks',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    params_json = models.TextField(
        default='{}',
        help_text='JSON string of task parameters (e.g. custom weights)',
    )
    task_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text='Hash for deduplication: user + model_type + params',
    )
    progress = models.PositiveIntegerField(default=0, help_text='0-100')
    total_paths = models.PositiveIntegerField(default=0)
    processed_paths = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    error_traceback = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Task {self.id} [{self.status}] - {self.model_type}"

    @classmethod
    def make_task_hash(cls, user_id, model_type, params_dict):
        raw = f"{user_id}:{model_type}:{json.dumps(params_dict, sort_keys=True)}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @property
    def params(self):
        try:
            return json.loads(self.params_json)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}

    def mark_running(self):
        from django.utils import timezone
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_success(self):
        from django.utils import timezone
        self.status = self.STATUS_SUCCESS
        self.finished_at = timezone.now()
        self.progress = 100
        self.save(update_fields=['status', 'finished_at', 'progress'])

    def mark_failed(self, error_message, error_traceback=''):
        from django.utils import timezone
        self.status = self.STATUS_FAILED
        self.finished_at = timezone.now()
        self.error_message = error_message[:500]
        self.error_traceback = error_traceback[:4000]
        self.save(update_fields=['status', 'finished_at', 'error_message', 'error_traceback'])

    def update_progress(self, processed, total):
        self.processed_paths = processed
        self.total_paths = total
        if total > 0:
            self.progress = min(100, int((processed / total) * 100))
        self.save(update_fields=['processed_paths', 'total_paths', 'progress'])


class AttributionResult(models.Model):
    MODEL_CHOICES = [
        ('first_touch', 'First Touch'),
        ('last_touch', 'Last Touch'),
        ('linear', 'Linear'),
        ('custom_weight', 'Custom Weight'),
    ]

    task = models.ForeignKey(
        AttributionTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='results',
    )
    model_type = models.CharField(max_length=50, choices=MODEL_CHOICES)
    channel = models.ForeignKey(AdChannel, on_delete=models.CASCADE, related_name='attribution_results')
    credit = models.DecimalField(max_digits=14, decimal_places=4)
    calculated_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attribution_results',
    )
    is_partial = models.BooleanField(
        default=False,
        help_text='True if result was persisted before task completion (partial save)',
    )

    class Meta:
        ordering = ['-calculated_at', '-credit']

    def __str__(self):
        return f"{self.model_type} - {self.channel.name}: {self.credit}"
