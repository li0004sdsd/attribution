from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('attribution', '0002_attributionresult_created_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttributionTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_type', models.CharField(
                    choices=[
                        ('first_touch', 'First Touch'),
                        ('last_touch', 'Last Touch'),
                        ('linear', 'Linear'),
                        ('custom_weight', 'Custom Weight'),
                    ],
                    max_length=50,
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', '待执行'),
                        ('running', '执行中'),
                        ('success', '成功'),
                        ('failed', '失败'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('params_json', models.TextField(
                    default='{}',
                    help_text='JSON string of task parameters (e.g. custom weights)',
                )),
                ('task_hash', models.CharField(
                    db_index=True,
                    help_text='Hash for deduplication: user + model_type + params',
                    max_length=64,
                )),
                ('progress', models.PositiveIntegerField(default=0, help_text='0-100')),
                ('total_paths', models.PositiveIntegerField(default=0)),
                ('processed_paths', models.PositiveIntegerField(default=0)),
                ('error_message', models.TextField(blank=True, default='')),
                ('error_traceback', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='attribution_tasks',
                    to='auth.user',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='attributionresult',
            name='task',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='results',
                to='attribution.attributiontask',
            ),
        ),
        migrations.AddField(
            model_name='attributionresult',
            name='is_partial',
            field=models.BooleanField(
                default=False,
                help_text='True if result was persisted before task completion (partial save)',
            ),
        ),
        migrations.AlterField(
            model_name='attributionresult',
            name='model_type',
            field=models.CharField(
                choices=[
                    ('first_touch', 'First Touch'),
                    ('last_touch', 'Last Touch'),
                    ('linear', 'Linear'),
                    ('custom_weight', 'Custom Weight'),
                ],
                max_length=50,
            ),
        ),
    ]
