from __future__ import unicode_literals
import logging

from django.db import migrations
from django_bulk_update.helper import bulk_update

logger = logging.getLogger(__file__)


def update_comment_root_target(state, *args, **kwargs):
    Comment = state.get_model('osf', 'comment')
    comments = Comment.objects.exclude(is_deleted=True).select_related('root_target')
    logger.info('{} comments to check'.format(comments.count()))
    comments_to_update = []
    for comment in comments:
        if comment.root_target:
            root_target_ctype = comment.root_target.content_type
            root_target_model_cls = state.get_model(root_target_ctype.app_label, root_target_ctype.model)
            root_target = root_target_model_cls.objects.get(pk=comment.root_target.object_id)
            if hasattr(root_target, 'is_deleted') and root_target.is_deleted:
                logger.info('{} is deleted. Setting Comment {} root_target to None'.format(root_target, comment.pk))
                comment.root_target = None
                comments_to_update.append(comment)
            if hasattr(root_target, 'deleted') and root_target.deleted:
                logger.info('{} is deleted. Setting Comment {} root_target to None'.format(root_target, comment.pk))
                comment.root_target = None
                comments_to_update.append(comment)
    bulk_update(comments_to_update, update_fields=['root_target'])
    logger.info('Total comments migrated: {}'.format(len(comments_to_update)))


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0098_merge_20180416_1807'),
    ]

    operations = [
        migrations.RunPython(update_comment_root_target)
    ]
