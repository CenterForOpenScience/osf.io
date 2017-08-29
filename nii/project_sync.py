#!/usr/bin/env python

import os
import sys
import json
import time
import datetime as dt
from logging import getLogger

import requests

from website.app import init_app
from website import settings

logger = getLogger(__name__)

CERT = settings.GAKUNIN_SP_CERT
KEY  = settings.GAKUNIN_SP_KEY
HOST = settings.CLOUD_GATAWAY_HOST

def json_print(text):
    json.dump(json.loads(text), sys.stdout, indent=4, separators=(',', ': '))


def cg_api_init():
    return requests.Session()


### using People API for Cloud Gateway.
### see https://meatwiki.nii.ac.jp/confluence/display/gakuninmappublic/API
def cg_api_people(cgapi, group, is_admin):
    admin = ''
    if is_admin:
        admin = '%2Fadmin'
    path = '/api/people/@me/' + group + admin + '?lang=en'
    r = cgapi.get('https://' + HOST + path, verify=True, cert=(CERT, KEY))
    if r.status_code == 403 or r.status_code == 404:
        return (404, None)
    elif r.status_code != 200:
        return (r.status_code, None)

    text = r.text
    try:
        #json_print(text)
        obj = json.loads(text)
        return (200, obj)
    except:
        logger.warning('unexpected response from Cloud Gateway')
        return (500, None)


def is_node_admin(node, user):
    return node.has_permission(user, 'admin', check_parent=False)


def log_event(eventname, group, username):
    #print '{}: group={}, username={}'.format(eventname, group, username)
    logger.info('{}: group={}, username={}'.format(eventname, group, username))


def leave_group_project_sync(node, dict_new_contributors):
    from framework.auth import Auth

    # leave this project
    for contri_user in node.contributors:
        if contri_user.id in dict_new_contributors:
            continue  # OK

        auth = Auth(user=contri_user)
        if not is_node_admin(node, contri_user):
            log_event('REMOVE_USER', node.group.name, contri_user.username)
            node.remove_contributor(contri_user, auth=auth, log=True)
            continue
        admin_users = list(node.get_admin_contributors(node.contributors))
        if len(admin_users) > 1:
            log_event('REMOVE_ADMIN', node.group.name, contri_user.username)
            node.remove_contributor(contri_user, auth=auth, log=True)
            continue
        ### The user is last admin.
        ### len(node.contributors) may not be 1.
        log_event('HIDE_PROJECT', node.group.name, contri_user.username)
        node.remove_node(auth)  # node.is_deleted = True


def project_sync_one(node, cgapi=None):
    from osf.models.user import OSFUser
    from modularodm import Q
    from website.util.permissions import CREATOR_PERMISSIONS, DEFAULT_CONTRIBUTOR_PERMISSIONS

    if not node.group:
        return

    logger.info('project_sync_one() start: group=' + node.group.name)
    if cgapi is None:
        cgapi = cg_api_init()
    (status_users, o_users) = cg_api_people(cgapi, node.group.name, False)
    (status_admins, o_admins) = cg_api_people(cgapi, node.group.name, True)
    if status_users == 404 and status_admins == 404:
        logger.warning('unknown group on Cloud Gateway: group=' +
                       node.group.name)
        if not node.is_deleted:
            leave_group_project_sync(node, {})   # clear
        return
    elif o_users is None or o_admins is None:
        logger.error('error on Cloud Gateway?: group=' + node.group.name +
                     ', status_userAPI=' + str(status_users) +
                     ', status_adminAPI=' + str(status_admins))
        return

    dict_admins = {}
    admin_entries = o_admins['entry'] if o_admins.has_key('entry') else {}
    for entry in admin_entries:
        if not entry.has_key('id'):
            continue
        i = entry['id']  # eptid
        if i is not None and i != '':
            dict_admins[i] = True

    dict_new_contributors = {}
    user_entries = o_users['entry'] if o_users.has_key('entry') else {}
    for entry in user_entries:
        if not entry.has_key('id'):
            continue
        eptid = entry['id']  # eptid
        try:
            user = OSFUser.objects.get(eptid=eptid)
        except Exception as e:
            # unknown user
            #logger.warning('unknown user (eptid=' + eptid + '): ' +
            #               str(e.args))
            continue
        if user is None:
            continue

        dict_new_contributors[user.id] = user
        group_admin = dict_admins.has_key(eptid)

        if node.is_deleted == True and group_admin:
            log_event('RE-OPEN', node.group.name, user.username)
            node.is_deleted = False   # re-enabled

        if node.is_contributor(user):
            if is_node_admin(node, user):
                if not group_admin:
                    log_event('ADMINtoUSER', node.group.name, user.username)
                    node.set_permissions(user,
                                         DEFAULT_CONTRIBUTOR_PERMISSIONS,
                                         save=False)
            else:
                if group_admin:
                    log_event('USERtoADMIN', node.group.name, user.username)
                    node.set_permissions(user, CREATOR_PERMISSIONS,
                                         save=False)
        elif group_admin:
            log_event('NEW_ADMIN', node.group.name, user.username)
            node.add_contributor(user, log=True, save=False,
                                 permissions=CREATOR_PERMISSIONS)
        else:  # not admin
            log_event('NEW_USER', node.group.name, user.username)
            node.add_contributor(user, log=True, save=False)
    node.save()
    if not node.is_deleted:
        leave_group_project_sync(node, dict_new_contributors)


def project_sync_all():
    from osf.models.node import Node

    logger.info('project_sync_all() start: ppid=' + str(os.getppid()) +
                ',pid=' + str(os.getpid()))
    cgapi = cg_api_init()
    for node in Node.find():
        #print "Node: title={}, group={}".format(node.title, node.group)
        project_sync_one(node, cgapi)
    logger.info('project_sync_all() finished')


LOOP_INTERAVAL = settings.PROJECT_SYNC_LOOP_INTERVAL  # sec.
TIME_LENGTH = settings.PROJECT_SYNC_TIME_LENGTH  # sec.

CHECK_INTERVAL = 10  # sec.

def user_last_access_get_latest():
    from osf.models.user import OSFUser

    latest = dt.datetime.min
    for user in OSFUser.find():
        if not hasattr(user, 'date_last_access'):
            continue
        elif type(user.date_last_access) is not dt.datetime:
            continue
        elif user.date_last_access > latest:
            latest = user.date_last_access
    return latest


def project_sync_loop():
    logger.info('project_sync_loop() start: ppid=' + str(os.getppid()) +
                ', pid=' + str(os.getpid()))
    init_app(routes=False, set_backends=False)

    time_len = dt.timedelta(seconds=TIME_LENGTH)
    while True:
        if dt.datetime.utcnow() < user_last_access_get_latest() + time_len:
            project_sync_all()
            time.sleep(LOOP_INTERAVAL)
        else:
            time.sleep(CHECK_INTERVAL)


def project_sync_detach():
    logger.info('project_sync_detach() called: ppid=' +
                str(os.getppid()) + ', pid=' + str(os.getpid()))
    from multiprocessing import Process
    p = Process(target=project_sync_loop)
    p.start()
    return p


def project_sync_enabled():
    return settings.PROJECT_SYNC

if __name__ == '__main__':
    init_app(routes=False, set_backends=False)
    project_sync_all()
