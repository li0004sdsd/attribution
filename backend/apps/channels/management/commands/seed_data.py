from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from apps.channels.models import AdChannel
from apps.journeys.models import ConversionPath, TouchPoint
import random


class Command(BaseCommand):
    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')

        channels_data = [
            ('Google Search', 'google', 1.20),
            ('Google Display', 'google', 0.45),
            ('Facebook Feed', 'facebook', 0.85),
            ('Facebook Stories', 'facebook', 0.60),
            ('LinkedIn Sponsored', 'linkedin', 3.50),
            ('Email Newsletter', 'email', 0.02),
            ('Organic Search', 'organic', 0.00),
            ('TikTok Video', 'tiktok', 0.55),
        ]

        channels = []
        for name, platform, cpc in channels_data:
            ch, _ = AdChannel.objects.get_or_create(
                name=name,
                defaults={'platform': platform, 'cost_per_click': cpc, 'active': True},
            )
            channels.append(ch)

        if ConversionPath.objects.count() < 50:
            for i in range(80):
                converted = random.random() > 0.3
                now = timezone.now()
                path = ConversionPath.objects.create(
                    user_id=f'user_{1000 + i}',
                    converted=converted,
                    conversion_value=round(random.uniform(50, 500), 2) if converted else 0,
                    conversion_time=now,
                )
                num_touches = random.randint(1, 5)
                selected = random.sample(channels, min(num_touches, len(channels)))
                for pos, ch in enumerate(selected, 1):
                    days_ago = random.randint(1, 60) if converted else random.randint(1, 10)
                    tp_time = now - timezone.timedelta(days=days_ago)
                    TouchPoint.objects.create(
                        path=path,
                        channel=ch,
                        timestamp=tp_time,
                        position=pos,
                    )

        self.stdout.write(self.style.SUCCESS('Seed data created.'))
