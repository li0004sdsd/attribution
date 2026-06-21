from django.db import models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('attribution', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attributionresult',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='attribution_results',
                to='auth.user',
            ),
        ),
    ]
