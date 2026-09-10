# Generated manually to reconcile migration leaves after merging develop
# into feature/prevent-project-creation (again).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0053_gdpr_delete_and_orcid_revoke'),
        ('osf', '0053_merge_20260901_reconcile'),
    ]

    operations = [
    ]
