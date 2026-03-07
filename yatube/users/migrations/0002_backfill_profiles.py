from django.conf import settings
from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    user_app_label, user_model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(user_app_label, user_model_name)
    Profile = apps.get_model('users', 'Profile')

    existing_user_ids = set(Profile.objects.values_list('user_id', flat=True))
    missing_profiles = [
        Profile(user_id=user.id)
        for user in User.objects.only('id')
        if user.id not in existing_user_ids
    ]
    if missing_profiles:
        Profile.objects.bulk_create(missing_profiles)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_missing_profiles, migrations.RunPython.noop),
    ]
