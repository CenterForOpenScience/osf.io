from django.db import migrations


DASHBOARD_GROUP_NAME = 'download_telemetry'


def grant_staff_access(apps, schema_editor):
    """Let the allow-listed users through Django's admin door.

    ``AdminSite.has_permission`` rejects anyone without ``is_staff`` before any
    per-model check runs, so without this the dashboard is unreachable for exactly
    the people it was built for.

    This is not superuser.  These accounts carry no Django permissions, so the
    download events page is the only thing in the admin they can open — every other
    registered model stays hidden and unviewable.  Kept separate from the migration
    that creates the group so it also applies to databases where that one has
    already run.
    """
    Group = apps.get_model('auth', 'Group')
    group = Group.objects.filter(name=DASHBOARD_GROUP_NAME).first()
    if group is None:
        return
    group.user_set.filter(is_staff=False).update(is_staff=True)


def revoke_staff_access(apps, schema_editor):
    """Deliberately a no-op.

    Some of these accounts are OSF admins who had staff access long before this
    feature; reversing the migration must not strip it from them, and we have no
    record of who had it beforehand.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0045_downloadevent'),
    ]

    operations = [
        migrations.RunPython(grant_staff_access, revoke_staff_access),
    ]
