from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_auto_20260304_1113'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='follow',
            constraint=models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='prevent_self_follow',
            ),
        ),
    ]
