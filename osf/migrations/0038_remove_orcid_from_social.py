from django.db import migrations


def remove_orcid_from_social(apps, schema_editor):
    from osf.models import OSFUser
    users_with_orcid = OSFUser.objects.filter(social__has_key='orcid')
    users_to_update = []
    for user in users_with_orcid:
        user.social.pop('orcid', None)
        users_to_update.append(user)
    if users_to_update:
        OSFUser.objects.bulk_update(users_to_update, ['social'], batch_size=1000)
        # update share and elastic too
        for user in users_to_update:
            user.update_search()


def reverse(apps, schema_editor):
    """
    This is a no-op since we can't restore deleted records.
    """


class Migration(migrations.Migration):
    dependencies = [
        ('osf', '0037_notification_refactor_post_release'),
    ]

    operations = [
        migrations.RunPython(remove_orcid_from_social, reverse),
    ]
