from django.db import migrations
from osf.utils.styles import update_styles


def revert(state, schema):
    # The revert of this migration simply removes all CitationStyle instances.
    CitationStyle = state.get_model('osf', 'citationstyle')
    CitationStyle.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0106_citationstyle_parent_style'),
    ]

    operations = [
        migrations.RunPython(update_styles, revert),
    ]
