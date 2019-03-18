# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from osf.models import Guid, OSFUser, AbstractNode, FileInfo
from addons.osfstorage.models import OsfStorageFileNode
import logging

def used_quota(user_id):

    guid = Guid.objects.get(_id=user_id, content_type_id=ContentType.objects.get_for_model(OSFUser).id)

    user = OSFUser.objects.get(id=guid.object_id)
    projects = AbstractNode.objects.filter(creator_id=user.id)

    logging.info('num projects {}'.format(len(projects)))

    all_files = []
    for project in projects:
        logging.info('project id {}'.format(project.id))
        files = OsfStorageFileNode.objects.filter(
            target_object_id=project.id,
            target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
            deleted_on=None,
            deleted_by_id=None,
        )
        logging.info('num files {}'.format(len(files)))
        all_files += files

    total = 0

    logging.info('total num files {}'.format(len(all_files)))

    for file in all_files:
        logging.info('type {}'.format(file.type))
        fileinfo = FileInfo.objects.filter(file_id=file.id).first()
        if fileinfo:
            logging.info('size {}'.format(fileinfo.file_size))
            total += fileinfo.file_size

    return total
