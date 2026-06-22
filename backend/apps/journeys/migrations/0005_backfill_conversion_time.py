from django.db import migrations, models


def backfill_conversion_time(apps, schema_editor):
    """Backfill conversion_time with created_at for existing records."""
    ConversionPath = apps.get_model('journeys', 'ConversionPath')
    ConversionPath.objects.filter(conversion_time__isnull=True).update(
        conversion_time=models.F('created_at')
    )


def reverse_backfill(apps, schema_editor):
    """Reverse: set conversion_time back to null for records that match created_at."""
    ConversionPath = apps.get_model('journeys', 'ConversionPath')
    ConversionPath.objects.filter(
        conversion_time=models.F('created_at')
    ).update(conversion_time=None)


class Migration(migrations.Migration):

    dependencies = [
        ('journeys', '0004_add_conversion_time'),
    ]

    operations = [
        migrations.RunPython(backfill_conversion_time, reverse_backfill),
    ]
