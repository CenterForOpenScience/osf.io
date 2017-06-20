from django.db import migrations, models

class Migration(migrations.Migration):

    def fix_preprint_modified_dates(apps, schema):
        PreprintService = apps.get_model('osf.PreprintService')
        for preprint in PreprintService.objects.filter():
            if preprint.node.date_modified > preprint.date_modified:
                preprint.date_modified = preprint.node.date_modified
                preprint.save()

    dependencies = [('osf', '0039_maintenancestate')]

    operations = [
        migrations.RunPython(fix_preprint_modified_dates)

    ]
