# -*- coding: utf-8 -*-
from addons.base import signals as file_signals
from addons.osfstorage.models import OsfStorageFileNode
from api.base import settings as api_settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.db.models.functions import Coalesce
from osf.models import AbstractNode, FileLog, FileInfo, Guid, OSFUser, UserQuota


def used_quota(user_id):
    guid = Guid.objects.get(
        _id=user_id,
        content_type_id=ContentType.objects.get_for_model(OSFUser).id
    )
    projects = AbstractNode.objects.filter(creator_id=guid.object_id).all()
    projects_ids = list(map(lambda p: p.id, projects))

    files = OsfStorageFileNode.objects.filter(
        target_object_id__in=projects_ids,
        target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
        deleted_on=None,
        deleted_by_id=None,
    ).all()
    files_ids = list(map(lambda f: f.id, files))

    db_sum = FileInfo.objects.filter(file_id__in=files_ids).aggregate(
        filesize_sum=Coalesce(Sum('file_size'), 0))
    return db_sum['filesize_sum']

def abbreviate_size(size):
    size = float(size)
    abbr_dict = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}

    power = 0
    while size > 1024 and power < 4:
        size /= 1024
        power += 1

    return (size, abbr_dict[power])

@file_signals.file_updated.connect
def update_used_quota(self, target, user, event_type, payload):
    if event_type == FileLog.FILE_ADDED:
        file_size = int(payload['metadata']['size'])
        if file_size < 0:
            return
        try:
            user_quota = UserQuota.objects.get(
                user=target.creator,
                storage_type=UserQuota.NII_STORAGE
            )
            user_quota.used += file_size
            user_quota.save()
        except UserQuota.DoesNotExist:
            UserQuota.objects.create(
                user=target.creator,
                storage_type=UserQuota.NII_STORAGE,
                max_quota=api_settings.DEFAULT_MAX_QUOTA,
                used=file_size
            )
