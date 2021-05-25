from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0229_auto_20210317_2013'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='adminprofile',
            options={'permissions': (('view_management', 'Can view and run management commands in the admin app.'),)},
        ),
    ]
