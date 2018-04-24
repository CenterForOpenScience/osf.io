from __future__ import unicode_literals

from django.db import migrations
import logging

logger = logging.getLogger(__file__)


def update_comment_root_target(state, *args, **kwargs):
    Comment = state.get_model('osf', 'comment')
    comments = Comment.objects.filter(is_deleted=False)
    count = 0
    for comment in comments:
        if comment.root_target:
            if hasattr(comment.root_target.referent, 'is_deleted') and comment.root_target.referent.is_deleted:
                comment.root_target = None
                comment.save()
                count += 1
            if hasattr(comment.root_target.referent, 'deleted') and comment.root_target.referent.deleted:
                comment.root_target = None
                comment.save()
                count += 1
    logger.info('Total download number of commnet migrated is {}.'.format(count))


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0094_update_preprintprovider_group_auth'),
    ]

    operations = [
        migrations.RunPython(update_comment_root_target)
    ]