from django.db import migrations, transaction


def remove_orcid_from_social(apps, schema_editor):
    from osf.models import OSFUser

    user_ids = []
    batch = []
    CHUNK_SIZE = 1000

    for user in OSFUser.objects.filter(social__has_key='orcid').iterator(chunk_size=CHUNK_SIZE):
        user.social.pop('orcid', None)
        batch.append(user)
        user_ids.append(user.id)
        if len(batch) >= 1000:
            OSFUser.objects.bulk_update(batch, ['social'])
            batch.clear()

    if batch:
        OSFUser.objects.bulk_update(batch, ['social'])

    def reindex():
        for start in range(0, len(user_ids), CHUNK_SIZE):
            chunked_ids = user_ids[start:start + CHUNK_SIZE]
            for user in OSFUser.objects.filter(id__in=chunked_ids):
                user.update_search()

    if user_ids:
        # if update is successfully saved in database reindex share and elastic too
        transaction.on_commit(reindex)


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
