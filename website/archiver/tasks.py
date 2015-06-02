import requests
import json

import celery
from celery.utils.log import get_task_logger

from framework.tasks import app as celery_app
from framework.auth.core import User
from framework.exceptions import HTTPError

from website.archiver import (
    ARCHIVER_PENDING,
    ARCHIVER_CHECKING,
    ARCHIVER_SUCCESS,
    ARCHIVER_FAILURE,
    ARCHIVER_SENDING,
    ARCHIVER_SENT,
    ARCHIVER_SIZE_EXCEEDED,
    ARCHIVER_NETWORK_ERROR,
    ARCHIVER_UNCAUGHT_ERROR,
    AggregateStatResult,
)
from website.archiver import utils

from website.project.model import Node
from website.project import signals as project_signals
from website import settings
from website.app import init_addons, do_set_backends
from website.addons.base import StorageAddonBase

def create_app_context():
    try:
        init_addons(settings)
        do_set_backends(settings)
    except AssertionError:  # ignore AssertionErrors
        pass

logger = get_task_logger(__name__)

class ArchiverTask(celery.Task):
    abstract = True
    max_retries = 0

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        src = Node.load(kwargs['src_pk'])
        dst = Node.load(kwargs['dst_pk'])
        user = User.load(kwargs['user_pk'])
        if isinstance(exc, ArchiverSizeExceeded):
            utils.handle_archive_fail(
                ARCHIVER_SIZE_EXCEEDED,
                src, dst, user,
                exc.result
            )
        elif isinstance(exc, HTTPError):
            utils.handler_archive_fail(
                ARCHIVER_NETWORK_ERROR,
                src, dst, user,
                [exc.data['error']]
            )
        else:
            utils.handler_archive_fail(
                ARCHIVER_UNCAUGHT_ERROR,
                src, dst, user,
                [einfo]
            )
        raise exc

class ArchiverSizeExceeded(Exception):

    def __init__(self, result, *args, **kwargs):
        super(ArchiverSizeExceeded, self).__init__(*args, **kwargs)
        self.result = result

@celery_app.task(base=ArchiverTask, name="archiver.stat_addon")
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
    utils.update_status(dst, addon_short_name, ARCHIVER_CHECKING)
    src_addon = src.get_addon(addon_short_name)
    user = User.load(user_pk)
    file_tree = src_addon._get_file_tree(user=user)
    result = AggregateStatResult(
        src_addon._id,
        addon_short_name,
        targets=[utils.aggregate_file_tree_metadata(addon_short_name, file_tree, user)],
    )
    return result

@celery_app.task(name="archiver.make_copy_request")
def make_copy_request(dst_pk, url, data):
    """Make the copy request to the WaterBulter API and handle
    successful and fauled responses

    :param dst_pk: primary key of registration node
    :param url: URL to send request to
    :param data: <dict> of setting to send in POST to WaterBulter API
    :return: None
    """
    dst = Node.load(dst_pk)
    provider = data['source']['provider']
    utils.update_status(dst, provider, ARCHIVER_SENDING)
    logger.info("Sending copy request for addon: {0} on node: {1}".format(provider, dst_pk))
    res = requests.post(url, data=json.dumps(data))
    logger.info("Copy request responded with {0} for addon: {1} on node: {2}".format(res.status_code, provider, dst_pk))
    utils.update_status(dst, provider, ARCHIVER_SENT)
    if not res.ok:
        utils.update_status(
            dst,
            provider,
            ARCHIVER_FAILURE,
            meta={
                'errors': [res.json()]
            }
        )
    elif res.status_code in (200, 201):
        utils.update_status(dst, provider, ARCHIVER_SUCCESS)
    project_signals.archive_callback.send(dst)

@celery_app.task(base=ArchiverTask, name="archiver.archive_addon")
def archive_addon(addon_short_name, src_pk, dst_pk, user_pk, stat_result):
    """Archive the contents of an addon by making a copy request to the
    WaterBulter API

    :param addon_short_name: AddonConfig.short_name of the addon to be archived
    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: None
    """
    logger.info("Archiving addon: {0} on node: {1}".format(addon_short_name, src_pk))
    create_app_context()
    src = Node.load(src_pk)
    dst = Node.load(dst_pk)
    utils.update_status(dst, addon_short_name, ARCHIVER_PENDING, meta={
        'stat_result': str(stat_result),
    })
    user = User.load(user_pk)
    src_provider = src.get_addon(addon_short_name)
    folder_name = src_provider.archive_folder_name
    provider = src_provider.config.short_name
    cookie = user.get_or_create_cookie()
    data = {
        'source': {
            'cookie': cookie,
            'nid': src_pk,
            'provider': provider,
            'path': '/',
        },
        'destination': {
            'cookie': cookie,
            'nid': dst_pk,
            'provider': settings.ARCHIVE_PROVIDER,
            'path': '/',
        },
        'rename': folder_name,
    }
    copy_url = settings.WATERBUTLER_URL + '/ops/copy'
    make_copy_request.si(dst_pk, copy_url, data)()


@celery_app.task(base=ArchiverTask, name="archiver.archive_node")
def archive_node(results, src_pk, dst_pk, user_pk):
    """First use the results of #stat_node to check disk usage of the
    initated registration, then either fail the registration or
    create a celery.group group of subtasks to archive addons

    :param results: results from the #stat_addon subtasks spawned in #stat_node
    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: None
    """
    logger.info("Archiving node: {0}".format(src_pk))
    src = Node.load(src_pk)
    stat_result = AggregateStatResult(
        src_pk,
        src.title,
        targets=results,
    )
    if stat_result.disk_usage > settings.MAX_ARCHIVE_SIZE:
        raise ArchiverSizeExceeded(result=stat_result)
    else:
        celery.chain(
            archive_addon.si(
                addon_short_name=result.target_name,
                src_pk=src_pk,
                dst_pk=dst_pk,
                user_pk=user_pk,
                stat_result=result,
            )
            for result in stat_result.targets.values()
        ).apply_async()

@celery_app.task(bind=True, base=ArchiverTask, name='archiver.archive')
def archive(self, src_pk, dst_pk, user_pk):
    """Saves the celery task id, and start a celery.chord
    that runs stat_addon for each addon attached to the Node,
    then runs archive node with the result

    :param src_pk: primary key of node being registered
    :param dst_pk: primary key of registration node
    :param user_pk: primary key of registration initatior
    :return: None
    """
    logger = get_task_logger(__name__)
    logger.info("Received archive task for Node: {0} into Node: {1}".format(src_pk, dst_pk))
    dst = Node.load(dst_pk)
    user = User.load(user_pk)
    create_app_context()
    utils.link_archive_provider(dst, user)
    dst.archiving = True
    dst.archive_task_id = self.request.id
    dst.save()
    src = Node.load(src_pk)
    targets = [src.get_addon(name) for name in settings.ADDONS_ARCHIVABLE]
    celery.chord(
        celery.chain(
            stat_addon.si(
                addon_short_name=addon.config.short_name,
                src_pk=src_pk,
                dst_pk=dst_pk,
                user_pk=user_pk,
            )
            for addon in targets if (addon and isinstance(addon, StorageAddonBase))
        )
    )(archive_node.s(src_pk=src_pk, dst_pk=dst_pk, user_pk=user_pk))
