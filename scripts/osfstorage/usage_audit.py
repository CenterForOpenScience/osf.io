"""File: usage_audit.py
Find all users and projects where their total usage (current file + deleted files) is >= the set limit
Projects or users can have their GUID whitelisted via `usage_audit whitelist [GUID ...]`
User usage is defined as the total usage of all projects they have > READ access on
Project usage is defined as the total usage of it and all its children
total usage is defined as the sum of the size of all verions associated with X via OsfStorageFileNode and OsfStorageTrashedFileNode
"""

import os
import gc
import json
import logging
import functools

from collections import defaultdict
from django.contrib.contenttypes.models import ContentType

from tqdm import tqdm


from framework.celery_tasks import app as celery_app
from osf.models import TrashedFile, Node

from website import mails
from website.app import init_app
from website.settings.defaults import GBs

from scripts import utils as scripts_utils

# App must be init'd before django models are imported
init_app(set_backends=True, routes=False)

from osf.models import BaseFileNode, FileVersion, OSFUser, AbstractNode

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

USER_LIMIT = 5 * GBs
PROJECT_LIMIT = 5 * GBs

WHITE_LIST_PATH = os.path.join(os.path.dirname(__file__), 'usage_whitelist.json')


try:
    with open(WHITE_LIST_PATH, 'r') as fobj:
        WHITE_LIST = set(json.load(fobj))  # Cast to set for constant time look ups
    logger.info('Loaded whitelist.json from {}'.format(WHITE_LIST_PATH))
except IOError:
    WHITE_LIST = set()
    logger.warning('No whitelist found')


def add_to_white_list(gtg):
    gtg = set(gtg).difference(WHITE_LIST)
    logger.info('Adding {} to whitelist'.format(gtg))
    with open(WHITE_LIST_PATH, 'w') as fobj:
        json.dump(list(WHITE_LIST.union(gtg)), fobj)  # Sets are not JSON serializable
    logger.info('Whitelist updated to {}'.format(WHITE_LIST))


def get_usage(node):
    node_content_type = ContentType.objects.get_for_model(Node)

    vids = [each for each in BaseFileNode.active.filter(provider='osfstorage', target_object_id=node.id, target_content_type=node_content_type).values_list('versions', flat=True) if each]
    t_vids = [each for each in TrashedFile.objects.filter(provider='osfstorage', target_object_id=node.id, target_content_type=node_content_type).values_list('versions', flat=True) if each]

    usage = sum([v.size or 0 for v in FileVersion.objects.filter(id__in=vids)])
    trashed_usage = sum([v.size or 0 for v in FileVersion.objects.filter(id__in=t_vids)])

    return list(map(sum, zip(*([(usage, trashed_usage)] + [get_usage(child) for child in node.nodes_primary]))))  # Adds tuples together, map(sum, zip((a, b), (c, d))) -> (a+c, b+d)


def limit_filter(limit, item_usage_tuple):
    """Note: item_usage_tuple is a tuple(str(guid), tuple(current_usage, deleted_usage))"""
    item = item_usage_tuple[0]
    usage = item_usage_tuple[1]
    return item not in WHITE_LIST and sum(usage) >= limit


def main(send_email=False):
    logger.info('Starting Project storage audit')

    lines = []
    projects = {}
    users = defaultdict(lambda: (0, 0))

    top_level_nodes = AbstractNode.objects.get_roots()
    progress_bar = tqdm(total=top_level_nodes.count())
    top_level_nodes = top_level_nodes.iterator()

    for i, node in enumerate(top_level_nodes):
        progress_bar.update(i+1)
        if node._id in WHITE_LIST:
            continue  # Dont count whitelisted nodes against users
        projects[node._id] = get_usage(node)
        for contrib in node.contributors:
            if node.can_edit(user=contrib):
                users[contrib._id] = tuple(map(sum, zip(users[contrib._id], projects[node._id])))  # Adds tuples together, map(sum, zip((a, b), (c, d))) -> (a+c, b+d)

        if i % 25 == 0:
            gc.collect()
    progress_bar.close()

    for model, collection, limit in ((OSFUser, users, USER_LIMIT), (AbstractNode, projects, PROJECT_LIMIT)):
        for item, (used, deleted) in filter(functools.partial(limit_filter, limit), collection.items()):
            line = '{!r} has exceeded the limit {:.2f}GBs ({}b) with {:.2f}GBs ({}b) used and {:.2f}GBs ({}b) deleted.'.format(model.load(item), limit / GBs, limit, used / GBs, used, deleted / GBs, deleted)
            logger.info(line)
            lines.append(line)

    if lines:
        if send_email:
            logger.info('Sending email...')
            mails.send_mail('support+scripts@osf.io', mails.EMPTY, body='\n'.join(lines), subject='Script: OsfStorage usage audit', can_change_preferences=False,)
        else:
            logger.info('send_email is False, not sending email'.format(len(lines)))
        logger.info('{} offending project(s) and user(s) found'.format(len(lines)))
    else:
        logger.info('No offending projects or users found')


@celery_app.task(name='scripts.osfstorage.usage_audit')
def run_main(send_mail=False, white_list=None):
    scripts_utils.add_file_logger(logger, __file__)
    if white_list:
        add_to_white_list(white_list)
    else:
        main(send_mail)
