from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('journeys', '0005_backfill_conversion_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversionpath',
            name='conversion_time',
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                help_text='Timestamp when the conversion actually occurred',
            ),
        ),
    ]
