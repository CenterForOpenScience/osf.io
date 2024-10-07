# -*- coding: utf-8 -*-
import logging

from addons.base import signals as file_signals
from addons.osfstorage.models import OsfStorageFileNode, Region
from api.base import settings as api_settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.db.models.functions import Coalesce
from osf.models import (
    AbstractNode, BaseFileNode, FileLog, FileInfo, Guid, OSFUser, UserQuota,
    ProjectStorageType
)
from django.utils import timezone
from osf.utils.requests import check_select_for_update


PROVIDERS = ['s3compatinstitutions']

# import inspect
logger = logging.getLogger(__name__)


def used_quota(user_id, storage_type=UserQuota.NII_STORAGE):
    guid = Guid.objects.get(
        _id=user_id,
        content_type_id=ContentType.objects.get_for_model(OSFUser).id
    )
    projects_ids = AbstractNode.objects.filter(
        projectstoragetype__storage_type=storage_type,
        is_deleted=False,
        creator_id=guid.object_id
    ).values_list('id', flat=True)
    if storage_type != UserQuota.NII_STORAGE:
        files_ids = BaseFileNode.objects.filter(
            target_object_id__in=projects_ids,
            target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
            deleted_on=None,
            deleted_by_id=None,
        ).values_list('id', flat=True)
    else:
        files_ids = OsfStorageFileNode.objects.filter(
            target_object_id__in=projects_ids,
            target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
            deleted_on=None,
            deleted_by_id=None,
        ).values_list('id', flat=True)
    db_sum = FileInfo.objects.filter(file_id__in=files_ids).aggregate(
        filesize_sum=Coalesce(Sum('file_size'), 0))
    return db_sum['filesize_sum'] if db_sum['filesize_sum'] is not None else 0


def update_user_used_quota(user, storage_type=UserQuota.NII_STORAGE, is_recalculating_quota=False):
    """Update user's used quota

    - If the function is called in recalculate quota process and storage_type parameter is 2 (for NII Storage),
      update used quota for storage_type = 2 with total file size from projects with storage_type = 1 and 2
    - Otherwise, update used quota for specified storage_type with total file size from projects with that storage_type

    :param user: user to be updated used quota
    :param storage_type: storage type
    :param is_recalculating_quota: a boolean to know whether the function is used in recalculate quota process or not
    """
    if is_recalculating_quota and storage_type == UserQuota.CUSTOM_STORAGE:
        # If the function is called in recalculate quota process and storage_type parameter is 2 (for NII Storage),
        # get total file size of projects with storage_type 1 and 2
        used_quota_for_nii_default_storage = used_quota(user._id, UserQuota.NII_STORAGE)
        used_quota_for_nii_custom_storage = used_quota(user._id, UserQuota.CUSTOM_STORAGE)
        used = used_quota_for_nii_default_storage + used_quota_for_nii_custom_storage
    else:
        # Get total file size of projects with specified storage_type
        used = used_quota(user._id, storage_type)

    try:
        if check_select_for_update():
            user_quota = UserQuota.objects.filter(
                user=user,
                storage_type=storage_type,
            ).select_for_update().get()
        else:
            user_quota = UserQuota.objects.get(
                user=user,
                storage_type=storage_type,
            )
        user_quota.used = used
        user_quota.save()
    except UserQuota.DoesNotExist:
        UserQuota.objects.create(
            user=user,
            storage_type=storage_type,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=used,
        )


def abbreviate_size(size):
    size = float(size)
    abbr_dict = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}

    power = 0
    while size > api_settings.BASE_FOR_METRIC_PREFIX and power < 4:
        size /= api_settings.BASE_FOR_METRIC_PREFIX
        power += 1

    return (size, abbr_dict[power])

def get_quota_info(user, storage_type=UserQuota.NII_STORAGE):
    try:
        user_quota = user.userquota_set.get(storage_type=storage_type)
        return (user_quota.max_quota, user_quota.used)
    except UserQuota.DoesNotExist:
        return (api_settings.DEFAULT_MAX_QUOTA, used_quota(user._id, storage_type))

def get_project_storage_type(node):
    try:
        return ProjectStorageType.objects.get(node=node).storage_type
    except ProjectStorageType.DoesNotExist:
        return ProjectStorageType.NII_STORAGE

@file_signals.file_updated.connect
def update_used_quota(self, target, user, event_type, payload):
    data = dict(payload.get('metadata')) if payload.get('metadata') else None
    metadata_provider = data.get('provider') if payload.get('metadata') else None
    if metadata_provider == 'osfstorage' or metadata_provider in PROVIDERS:
        file_node = None
        action_payload = dict(payload).get('action')
        try:
            if metadata_provider in PROVIDERS:
                if data.get('kind') == 'folder' and action_payload == 'create_folder':
                    base_file_node = BaseFileNode(
                        type='osf.{}folder'.format(metadata_provider),
                        provider=metadata_provider,
                        _path=data.get('materialized'),
                        _materialized_path=data.get('materialized'),
                        target_object_id=target.id,
                        target_content_type=ContentType.objects.get_for_model(AbstractNode)
                    )
                    base_file_node.save()
                else:
                    file_node = BaseFileNode.objects.filter(
                        _path=data.get('materialized'),
                        name=data.get('name'),
                        provider=metadata_provider,
                        target_object_id=target.id,
                        deleted=None,
                        target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
                    ).order_by('-id').first()
            else:
                file_node = BaseFileNode.objects.get(
                    _id=data.get('path').strip('/'),
                    target_object_id=target.id,
                    target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
                )
        except BaseFileNode.DoesNotExist:
            logging.error('FileNode not found, cannot update used quota!')
            return

        storage_type = get_project_storage_type(target)
        if event_type == FileLog.FILE_ADDED:
            file_added(target, payload, file_node, storage_type)
        elif event_type == FileLog.FILE_REMOVED:
            if metadata_provider in PROVIDERS:
                if data.get('kind') == 'file':
                    file_node.is_deleted = True
                    file_node.deleted = timezone.now()
                    file_node.deleted_on = file_node.deleted
                    file_node.type = 'osf.trashedfile'
                    file_node.deleted_by_id = user.id
                    file_node.save()
                    node_removed(target, user, payload, file_node, storage_type)
                elif data.get('kind') == 'folder':
                    list_file_node = BaseFileNode.objects.filter(
                        _materialized_path__startswith=data.get('materialized'),
                        target_object_id=target.id,
                        provider=metadata_provider,
                        deleted=None,
                        target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
                    ).all()
                    for file_node_remove in list_file_node:
                        file_node_remove.is_deleted = True
                        if file_node_remove.type == 'osf.{}file'.format(metadata_provider):
                            file_node_remove.type = 'osf.trashedfile'
                        elif file_node_remove.type == 'osf.{}folder'.format(metadata_provider):
                            file_node_remove.type = 'osf.trashedfolder'
                        file_node_remove.deleted = timezone.now()
                        file_node_remove.deleted_on = file_node_remove.deleted
                        file_node_remove.deleted_by_id = user.id
                        file_node_remove.save()
                        if file_node_remove.type == 'osf.trashedfile':
                            node_removed(target, user, payload, file_node_remove, storage_type)
            else:
                node_removed(target, user, payload, file_node, storage_type)
        elif event_type == FileLog.FILE_UPDATED:
            file_modified(target, user, payload, file_node, storage_type)
    else:
        return


def file_added(target, payload, file_node, storage_type):
    file_size = int(payload['metadata']['size'])
    if file_size < 0:
        return
    try:
        if check_select_for_update():
            user_quota = UserQuota.objects.filter(
                user=target.creator,
                storage_type=storage_type
            ).select_for_update().get()
        else:
            user_quota = UserQuota.objects.get(
                user=target.creator,
                storage_type=storage_type
            )
        user_quota.used += file_size
        user_quota.save()
    except UserQuota.DoesNotExist:
        UserQuota.objects.create(
            user=target.creator,
            storage_type=storage_type,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=file_size
        )

    FileInfo.objects.create(file=file_node, file_size=file_size)

def node_removed(target, user, payload, file_node, storage_type):
    if check_select_for_update():
        user_quota = UserQuota.objects.filter(
            user=target.creator,
            storage_type=storage_type
        ).select_for_update().first()
    else:
        user_quota = UserQuota.objects.filter(
            user=target.creator,
            storage_type=storage_type
        ).first()
    if user_quota is not None:
        if 'osf.trashed' not in file_node.type:
            logging.error('FileNode is not trashed, cannot update used quota!')
            return

        for removed_file in get_node_file_list(file_node):
            try:
                if check_select_for_update():
                    file_info = FileInfo.objects.filter(file=removed_file).select_for_update().get()
                else:
                    file_info = FileInfo.objects.get(file=removed_file)
            except FileInfo.DoesNotExist:
                logging.error('FileInfo not found, cannot update used quota!')
                continue

            user_quota.used -= file_info.file_size
            if user_quota.used < 0:
                user_quota.used = 0
            file_info.file_size = 0
            file_info.save()
        user_quota.save()

def file_modified(target, user, payload, file_node, storage_type):
    file_size = int(payload['metadata']['size'])
    if file_size < 0:
        return

    if check_select_for_update():
        user_quota, _ = UserQuota.objects.select_for_update().get_or_create(
            user=target.creator,
            storage_type=storage_type,
            defaults={'max_quota': api_settings.DEFAULT_MAX_QUOTA}
        )
    else:
        user_quota, _ = UserQuota.objects.get_or_create(
            user=target.creator,
            storage_type=storage_type,
            defaults={'max_quota': api_settings.DEFAULT_MAX_QUOTA}
        )

    try:
        if check_select_for_update():
            file_info = FileInfo.objects.filter(file=file_node).select_for_update().get()
        else:
            file_info = FileInfo.objects.get(file=file_node)
    except FileInfo.DoesNotExist:
        file_info = FileInfo(file=file_node, file_size=0)

    user_quota.used += file_size - file_info.file_size
    if user_quota.used < 0:
        user_quota.used = 0
    user_quota.save()

    file_info.file_size = file_size
    file_info.save()

def update_default_storage(user):
    # logger.info('----{}::{}({})from:{}::{}({})'.format(inspect.getframeinfo(inspect.currentframe())[0], inspect.getframeinfo(inspect.currentframe())[2], inspect.getframeinfo(inspect.currentframe())[1], inspect.stack()[1][1], inspect.stack()[1][3], inspect.stack()[1][2]))
    # logger.info(user)
    if user is not None:
        user_settings = user.get_addon('osfstorage')
        if user_settings is None:
            user_settings = user.add_addon('osfstorage')
        institution = user.affiliated_institutions.first()
        if institution is not None:
            try:
                # logger.info(u'Institution: {}'.format(institution.name))
                region = Region.objects.get(_id=institution._id)
            except Region.DoesNotExist:
                # logger.info('Inside update_default_storage: region does not exist.')
                pass
            else:
                if user_settings.default_region._id != region._id:
                    user_settings.set_region(region._id)
                    logger.info(u'user={}, institution={}, user_settings.set_region({})'.format(user, institution.name, region.name))

def update_node_storage(node):
    if node is not None:
        node_settings = node.get_addon('osfstorage')
        if node_settings is None:
            node_settings = node.add_addon('osfstorage')
        institution = node.affiliated_institutions.first()
        if institution is not None:
            try:
                # logger.info(u'Institution: {}'.format(institution.name))
                region = Region.objects.get(_id=institution._id)
            except Region.DoesNotExist:
                # logger.info('Inside update_default_storage: region does not exist.')
                pass
            else:
                if node_settings.region._id != region._id:
                    node_settings.set_region(region._id)
                    logger.info(u'node={}, institution={}, node_settings.set_region({})'.format(node, institution.name, region.name))

def get_node_file_list(file_node):
    if 'file' in file_node.type:
        return [file_node]

    file_list = []
    folder_list = [file_node]

    while len(folder_list) > 0:
        folder_id_list = list(map(lambda f: f.id, folder_list))
        folder_list = []
        for child_file_node in BaseFileNode.objects.filter(parent_id__in=folder_id_list):
            if 'folder' in child_file_node.type:
                folder_list.append(child_file_node)
            else:  # file
                file_list.append(child_file_node)

    return file_list
