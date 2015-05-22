import requests
import json

from celery import group, chain
from celery.utils.log import get_task_logger

from framework.tasks import app as celery_app
from framework.auth.core import User
from framework.archiver import mails
from framework.archiver import (
    AggregateStatResult,
)
from framework.archiver.exceptions import ArchiverSizeExceeded
from framework.archiver import (
    ARCHIVER_PENDING,
    ARCHIVER_CHECKING,
    ARCHIVER_SUCCESS,
    ARCHIVER_SENDING,
    ARCHIVER_SENT
)
from framework.archiver.settings import (
    ARCHIVE_PROVIDER,
    MAX_ARCHIVE_SIZE,
)
from framework.archiver.utils import (
    catch_archive_addon_error,
    archive_folder_name,
    update_status,
    aggregate_file_tree_metadata,
)

from website.project.model import Node
from website.project import signals as project_signals
from website.mails import send_mail
from website import settings
from website.app import init_addons, do_set_backends

def create_app_context():
    try:
        init_addons(settings)
        do_set_backends(settings)
    except AssertionError:  # ignore AssertionErrors
        pass

logger = get_task_logger(__name__)

@celery_app.task(name="archiver.stat_addon")
def stat_addon(addon_short_name, src_pk, dst_pk, user_pk):
    """Collect metadata about the file tree of a given addon

    :param addon_short_name: AddonConfig.short_name of the addon to be examined
    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: AggregateStatResult containing file tree metadata
    """
    create_app_context()
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    update_status(dst, addon_short_name, ARCHIVER_CHECKING)
    src_addon = src.get_addon(addon_short_name)
    user = User.load(user_pk)
    file_tree = src_addon._get_file_tree(user=user)
    result = AggregateStatResult(
        src_addon._id,
        addon_short_name,
        targets=[aggregate_file_tree_metadata(addon_short_name, file_tree, user)],
    )
    return result

@celery_app.task(name="archiver.stat_node")
def stat_node(src_pk, dst_pk, user_pk):
    """Create a celery.group group of #stat_addon subtasks

    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: celery.result.GroupResult containing the collected return
    values of a #stat_addon
    """
    logger.info("Statting node: {0}".format(src_pk))
    create_app_context()
    src = Node.load(src_pk)
    targets = [src.get_addon(name) for name in settings.ADDONS_ARCHIVABLE]
    return group(
        stat_addon.si(
            addon.config.short_name,
            src_pk,
            dst_pk,
            user_pk,
        )
        for addon in targets if addon
    )()

@celery_app.task(name="archiver.make_copy_request")
def make_copy_request(dst_pk, url, data):
    """Make the copy request to the WaterBulter API and handle
    successful and fauled responses

    :param dst_pk: primary key of registration node
    :param url: URL to send request to
    :parama data: <dict> of setting to send in POST to WaterBulter API
    :return: None
    """
    dst = Node.load(dst_pk)
    provider = data['source']['provider']
    update_status(dst, provider, ARCHIVER_SENDING)
    logger.info("Sending copy request for addon: {0} on node: {1}".format(provider, dst_pk))
    res = requests.post(url, data=json.dumps(data))
    logger.info("Copy request responded with {2} for addon: {0} on node: {1}".format(provider, dst_pk, res.status_code))
    update_status(dst, provider, ARCHIVER_SENT)
    if res.status_code not in (200, 201, 202):
        catch_archive_addon_error(dst, provider, errors=[res.json()])
    elif res.status_code in (200, 201):
        update_status(dst, provider, ARCHIVER_SUCCESS)
    project_signals.archive_callback.send(dst)

@celery_app.task(name="archiver.archive_addon")
def archive_addon(addon_short_name, src_pk, dst_pk, user_pk, stat_result):
    """Archive the contents of an addon by making a copy request to the
    WaterBulter API

    :param addon_short_name: AddonConfig.short_name of the addon to be archived
    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: None
    """
    logger.info("Archiving addon: {1} on node: {0}".format(src_pk, addon_short_name))
    create_app_context()
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    update_status(dst, addon_short_name, ARCHIVER_PENDING, meta={
        'stat_result': str(stat_result),
    })
    user = User.load(user_pk)
    src_provider = src.get_addon(addon_short_name)
    folder_name = archive_folder_name(src_provider)
    provider = src_provider.config.short_name
    cookie = user.get_or_create_cookie()
    data = dict(
        source=dict(
            cookie=cookie,
            nid=src_pk,
            provider=provider,
            path='/',
        ),
        destination=dict(
            cookie=cookie,
            nid=dst_pk,
            provider=ARCHIVE_PROVIDER,
            path='/',
        ),
        rename=folder_name
    )
    copy_url = settings.WATERBUTLER_URL + '/ops/copy'
    make_copy_request.si(dst_pk, copy_url, data)()


@celery_app.task(name="archiver.archive_node")
def archive_node(group_result, src_pk, dst_pk, user_pk):
    """First use the result of #stat_node to check disk usage of the
    initated registration, then either fail the registration or
    create a celery.group group of subtasks to archive addons

    :param group_result: a celery.result.GroupResult containing the collected
    results from the #stat_addon subtasks spawned in #stat_node
    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: None
    """
    logger.info("Archiving node: {0}".format(src_pk))
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    user = User.load(user_pk)
    stat_result = AggregateStatResult(
        src_pk,
        src.title,
        targets=[result.result for result in group_result.results]
    )
    if stat_result.disk_usage > MAX_ARCHIVE_SIZE:
        raise ArchiverSizeExceeded(
            src,
            dst,
            user,
            stat_result
        )
    group(
        archive_addon.si(
            result.target_name,
            src_pk,
            dst_pk,
            user_pk,
            result,
        )
        for result in stat_result.targets.values()
    )()

@celery_app.task(bind=True, name='archiver.archive')
def archive(self, src_pk, dst_pk, user_pk):
    """Create a celery.chain task chain for first examining the file trees
    of a Node and its associated addons, then archiving that Node.

    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: None
    """
    dst = Node.load(dst_pk)
    dst.archiving = True
    dst.archive_task_id = self.request.id
    dst.save()
    chain(stat_node.si(src_pk, dst_pk, user_pk), archive_node.s(src_pk, dst_pk, user_pk))()


@celery_app.task
def send_success_message(dst_pk):
    """Send success email when archive completes

    :param dst_pk: primary key of registration Node
    :return: None
    """
    dst = Node.load(dst_pk)
    user = dst.creator

    send_mail(
        to_addr=user.username,
        mail=mails.ARCHIVE_SUCCESS,
        user=user,
        src=dst,
        mimetype='html',
    )
