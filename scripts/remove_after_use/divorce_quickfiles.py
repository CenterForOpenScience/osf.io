from osf.models import QuickFolder, OSFUser, UserLog
from osf.models.legacy_quickfiles import QuickFilesNode
from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery, Count
from django.contrib.contenttypes.models import ContentType

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def transfer_logs(quickfiles_node):
    """
    Recasts logs and saves them, old logs will be deleted with all quickfilesnodes.
    :param quickfiles_node: a QuickFilesNode
    :return:
    """
    for log in quickfiles_node.logs.all():
        log.__class__ = UserLog
        log.save()


def reverse_transfer_logs(quickfiles_node):
    """
    Recasts logs and saves them, old logs will be deleted with all quickfilesnodes.
    :param quickfiles_node: a QuickFilesNode
    :return:
    """
    for log in quickfiles_node.logs.all():
        log.__class__ = NodeLog
        log.save()


def create_quickfolders():
    """
    Bulk creates a Quickfolder for every user.
    :return:
    """
    users = OSFUser.objects.all()
    user_content_type_id = ContentType.objects.get_for_model(OSFUser).id
    quickfolder_content_type_id = ContentType.objects.get_for_model(QuickFolder).id

    paginated_users = Paginator(users, 1000)
    logger.info('There are {} '.format(users.count()))

    total_created = 0
    quickfolders_to_create = []
    for page_num in paginated_users.page_range:
        for user in paginated_users.page(page_num).object_list:
            quickfolder = QuickFolder(target_object_id=user.id,
                                      target_content_type_id=user_content_type_id,
                                      provider='osfstorage',
                                      path='/')

            quickfolders_to_create.append(quickfolder)

            total_created += 1
    QuickFolder.objects.bulk_create(quickfolders_to_create)
    logger.info('There are {} total quickfolders created'.format(total_created))


def reverse_create_quickfolders():
    """
    Bulk creates a Quickfolder for every user.
    :return:
    """
    users = OSFUser.objects.all()

    paginated_users = Paginator(users, 1000)
    logger.info('There are {} '.format(users.count()))

    total_created = 0
    for page_num in paginated_users.page_range:
        for user in paginated_users.page(page_num).object_list:
            QuickFilesNode.objects.create_for_user(user)
            total_created += 1

    logger.info('There are {} total quickfolders created'.format(total_created))


def repoint_guids():
    """
    This takes Guids from Quickfilesnode and repoints them at Quickfolders
    :return:
    """
    guids_repointed = 0

    quickfiles_nodes = QuickFilesNode.objects.all()
    paginated_quickfiles_nodes = Paginator(quickfiles_nodes, 1000)
    quickfolder_content_type_id = ContentType.objects.get_for_model(QuickFolder).id

    for page_num in paginated_quickfiles_nodes.page_range:
        for quickfiles_nodes in paginated_quickfiles_nodes.page(page_num).object_list:
            guid = quickfiles_nodes.guids.last()
            guid.referent = guid.referent.creator.quickfolder
            guid.object_id = guid.referent.target.quickfolder.id
            guid.content_type_id = quickfolder_content_type_id
            guid.save()
            guids_repointed += 1

    logger.info('There are {} total guids repointed to quickfolders'.format(guids_repointed))


def reverse_repoint_guids():
    """
    This takes Guids from Quickfilesnode and repoints them at Quickfolders
    :return:
    """
    guids_repointed = 0

    users = OSFUser.objects.all()

    paginated_users = Paginator(users, 1000)

    for page_num in paginated_users.page_range:
        for user in paginated_users.page(page_num).object_list:
            guid = user.guids.last()
            node = QuickFilesNode.objects.get_for_user(user)
            node.guids.add(guid)
            node.save()
            guids_repointed += 1

    logger.info('There are {} total guids repointed to quickfolders'.format(guids_repointed))


def migrate_quickfiles_to_quickfolders():
    """
    This migrates the actual files from Quickfilesnode to Quickfolders
    :return:
    """
    user_content_type_id = ContentType.objects.get_for_model(OSFUser).id
    find_quickfolders = Subquery(QuickFolder.objects.filter(target_object_id=OuterRef('id')).values('id'))
    users_ids_for_with_quickfiles = QuickFilesNode.objects.all().annotate(file_count=Count('files')).filter(file_count__gt=0).values_list('creator_id', flat=True)
    users_with_quickfiles = OSFUser.objects.filter(id__in=users_ids_for_with_quickfiles).annotate(_quickfolder=find_quickfolders).prefetch_related('guids')

    for user in users_with_quickfiles:
        try:
            quickfiles_node = QuickFilesNode.objects.get_for_user(user)
            quickfiles_node.files.update(parent_id=user._quickfolder,
                                         target_object_id=user.id,
                                         target_content_type_id=user_content_type_id)
        except QuickFilesNode.DoesNotExist as exc:
            logger.info('OSFUser {} does not have quickfiles'.format(user))
            raise exc

        transfer_logs(quickfiles_node)

    QuickFilesNode.objects.all().delete()


def reverse_migrate_quickfiles_to_quickfolders():
    """
    This migrates the actual files from Quickfilesnode to Quickfolders
    :return:
    """
    users = OSFUser.objects.all()
    quickfiles_type_id = ContentType.objects.get_for_model(QuickFilesNode).id

    for user in users:
        qf_node = QuickFilesNode.objects.get_for_user(user)
        user.quickfiles.update(parent_id=qf_node.files.last(),
                        target_object_id=qf_node.id,
                        target_content_type_id=quickfiles_type_id)
        reverse_transfer_logs(QuickFilesNode.objects.get_for_user(user))

    QuickFolder.objects.all().delete()


def divorce_quickfiles(state, schema):
    create_quickfolders()
    repoint_guids()
    migrate_quickfiles_to_quickfolders()


def reverse_divorce_quickfiles(state, schema):
    reverse_create_quickfolders()
    reverse_repoint_guids()
    reverse_migrate_quickfiles_to_quickfolders()
