from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('channels', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='adchannel',
            name='attribution_window_days',
            field=models.PositiveIntegerField(
                default=30,
                help_text='Number of days before conversion during which a touchpoint can contribute credit',
            ),
        ),
    ]
