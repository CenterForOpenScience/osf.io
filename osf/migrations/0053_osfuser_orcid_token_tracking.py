from django.db import migrations
import osf.utils.datetime_aware_jsonfield
import osf.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0052_downloadevent_download_channel'),
    ]

    operations = [
        migrations.AddField(
            model_name='osfuser',
            name='external_identity_access_token',
            field=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONField(blank=True, default=dict, encoder=osf.utils.datetime_aware_jsonfield.DateTimeAwareJSONEncoder),
        ),
    ]
