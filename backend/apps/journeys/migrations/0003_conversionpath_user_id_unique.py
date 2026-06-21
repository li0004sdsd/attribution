from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('journeys', '0002_deduplicate_conversion_paths'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversionpath',
            name='user_id',
            field=models.CharField(max_length=200, unique=True),
        ),
    ]
