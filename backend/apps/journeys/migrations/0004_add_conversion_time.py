from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('journeys', '0003_conversionpath_user_id_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversionpath',
            name='conversion_time',
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                null=True,
                help_text='Timestamp when the conversion actually occurred',
            ),
        ),
    ]
