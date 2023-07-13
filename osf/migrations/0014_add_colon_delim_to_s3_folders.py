from django.db import migrations
from addons.s3.utils import update_folder_names, reverse_update_folder_names


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0013_institution_support_email'),
    ]

    operations = [
        migrations.RunPython(update_folder_names, reverse_code=reverse_update_folder_names),
    ]
