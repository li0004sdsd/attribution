from django.db import migrations


def deduplicate_conversion_paths(apps, schema_editor):
    ConversionPath = apps.get_model('journeys', 'ConversionPath')
    user_groups = {}
    for path in ConversionPath.objects.order_by('created_at', 'pk'):
        user_groups.setdefault(path.user_id, []).append(path)

    ids_to_delete = []
    for user_id, paths in user_groups.items():
        if len(paths) <= 1:
            continue

        kept = None
        for p in paths:
            if p.converted:
                if kept is None or not kept.converted:
                    kept = p
                elif kept.converted and p.conversion_value > kept.conversion_value:
                    kept = p

        if kept is None:
            kept = paths[0]

        for p in paths:
            if p.pk != kept.pk:
                ids_to_delete.append(p.pk)

    if ids_to_delete:
        ConversionPath.objects.filter(pk__in=ids_to_delete).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('journeys', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(deduplicate_conversion_paths, migrations.RunPython.noop),
    ]
