# -*- coding: utf-8 -*-
# mAP core Group / Member syncronization


import time
import datetime
import logging
import os
import sys
import requests
import urllib
from operator import attrgetter
from pprint import pformat as pp

from urlparse import urlparse
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

# initialize for standalone exec
if __name__ == '__main__':
    logger.setLevel(level=logging.DEBUG)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    from website.app import init_app
    init_app(routes=False, set_backends=False)

from osf.models.user import OSFUser
from osf.models.node import Node
from osf.models.mapcore import MAPProfile

from website.util import web_url_for
from website.settings import (MAPCORE_HOSTNAME,
                              MAPCORE_AUTHCODE_PATH,
                              MAPCORE_TOKEN_PATH,
                              MAPCORE_CLIENTID,
                              MAPCORE_SECRET,
                              MAPCORE_AUTHCODE_MAGIC,
                              DOMAIN)
from nii.mapcore_api import (MAPCore, MAPCoreException, VERIFY,
                             mapcore_logger,
                             mapcore_group_member_is_private)
from django.core.exceptions import ObjectDoesNotExist

logger = mapcore_logger(logger)

# unicode to utf-8
def utf8(u):
    return u.encode('utf-8')

# utf-8 to unicode
def utf8dec(s):
    return s.decode('utf-8')

def mapcore_is_enabled():
    #sys.stderr.write('mapcore_is_enabled: MAPCORE_CLIENTID={}\n'.format(MAPCORE_CLIENTID))
    return True if MAPCORE_CLIENTID else False


# True or Exception
def mapcore_api_is_available(user):
    mapcore = MAPCore(user)
    mapcore.get_api_version()
    logger.debug('mapcore_api_is_available::Access Token (for {}) is up-to-date'.format(user.username))
    return True


def mapcore_log_error(msg):
    logger.error(msg)


#
# lock node or user
#
class MAPCoreLocker():
    def lock_user(self, user):
        while True:
            #print('before transaction.atomic')
            with transaction.atomic():
                #print('transaction.atomic start')
                u = OSFUser.objects.select_for_update().get(username=user.username)
                if not u.mapcore_api_locked:
                    #print('before lock')
                    #time.sleep(5) # for debug
                    u.mapcore_api_locked = True
                    u.save()
                    logger.debug('OSFUser(' + u.username + ').mapcore_api_locked=True')
                    return
            #print('cannot get lock, sleep 1')
            time.sleep(1)

    def unlock_user(self, user):
        with transaction.atomic():
            u = OSFUser.objects.select_for_update().get(username=user.username)
            u.mapcore_api_locked = False
            u.save()
            logger.debug('OSFUser(' + u.username + ').mapcore_api_locked=False')

    def lock_node(self, node):
        while True:
            with transaction.atomic():
                #print('transaction.atomic start')
                n = Node.objects.select_for_update().get(guids___id=node._id)
                if not n.mapcore_api_locked:
                    n.mapcore_api_locked = True
                    n.save()
                    logger.debug('Node(' + n._id + ').mapcore_api_locked=True')
                    return
            #print('cannot get lock, sleep 1')
            time.sleep(1)

    def unlock_node(self, node):
        with transaction.atomic():
            n = Node.objects.select_for_update().get(guids___id=node._id)
            print('n.mapcore_api_locked={}'.format(n.mapcore_api_locked))
            n.mapcore_api_locked = False
            n.save()
            logger.debug('Node(' + n._id + ').mapcore_api_locked=False')

locker = MAPCoreLocker()

def mapcore_unlock_all():
    logger.info('mapcore_unlock_all() start')
    with transaction.atomic():
        for user in OSFUser.objects.all():
            user.mapcore_api_locked = False
            user.save()
            logger.debug('mapcore_unlock_all(): User={}'.format(user.username))
        for node in Node.objects.all():
            node.mapcore_api_locked = False
            node.save()
            logger.debug('mapcore_unlock_all(): Node={}'.format(node._id))
    logger.info('mapcore_unlock_all() done')

def mapcore_request_authcode(**kwargs):
    '''
    get an authorization code from mAP. this process will redirect some times.
    :param params  dict of GET parameters in request
    '''

    # parameter check
    if 'request' in kwargs.keys():
        kwargs = kwargs['request']
    logger.debug('mapcore_request_authcode get params:\n')
    logger.debug(pp(kwargs))
    next_url = kwargs.get('next_url')
    if next_url is not None:
        state_str = next_url.encode('base64')
    else:
        state_str = MAPCORE_AUTHCODE_MAGIC

    # make call
    url = MAPCORE_HOSTNAME + MAPCORE_AUTHCODE_PATH
    redirect_uri = DOMAIN + web_url_for('mapcore_oauth_complete')[1:]
    logger.info('mapcore_request_authcode: redirect_uri is [' + redirect_uri + ']')
    params = {'response_type': 'code',
              'redirect_uri': redirect_uri,
              'client_id': MAPCORE_CLIENTID,
              'state': state_str}
    query = url + '?' + urllib.urlencode(params)
    logger.info('redirect to AuthCode request: ' + query)
    return query


def mapcore_receive_authcode(user, params):
    '''
    here is the starting point of user registraion for mAP
    :param user  OSFUser object of current user
    :param params   dict of url parameters in request
    '''
    logger.debug('get an oatuh response:')
    s = ''
    for k, v in params.items():
        s += '(' + k + ',' + v + ') '
    logger.debug('oauth returned parameters: ' + s)

    # authorization code check
    if 'code' not in params or 'state' not in params:
        raise ValueError('invalid response from oauth provider')

    # exchange autorization code to access token
    authcode = params['code']
    # authcode = 'AUTHORIZATIONCODESAMPLE'
    # eppn = 'foobar@esample.com'
    redirect_uri = DOMAIN + web_url_for('mapcore_oauth_complete')[1:]
    (access_token, refresh_token) = mapcore_get_accesstoken(authcode, redirect_uri)

    # set mAP attribute into current user
    with transaction.atomic():
        u = OSFUser.objects.select_for_update().get(username=user.username)
        if u.map_profile is None:
            map_profile = MAPProfile.objects.create()
            u.map_profile = map_profile
            u.save()
        else:
            map_profile = u.map_profile
        map_profile.oauth_access_token = access_token
        map_profile.oauth_refresh_token = refresh_token
        map_profile.oauth_refresh_time = timezone.now()
        map_profile.save()
        logger.debug('User [' + u.eppn + '] get access_token [' + access_token + '] -> saved')

    # DEBUG: read record and print
    """
    logger.info('In database:')
    me = OSFUser.objects.get(eppn=user.eppn)
    logger.info('name: ' + me.fullname)
    logger.info('eppn: ' + me.eppn)
    if me.map_profile:
        logger.info('access_token: ' + me.map_profile.oauth_access_token)
        logger.info('refresh_token: ' + me.map_profile.oauth_refresh_token)
    """

    if params['state'] != MAPCORE_AUTHCODE_MAGIC:
        return params['state'].decode('base64')  # user defined state string
    return DOMAIN   # redirect to home -> will redirect to dashboard


def mapcore_get_accesstoken(authcode, redirect):
    '''
    exchange authorization code to access token and refresh token
    API call returns the JSON response from mAP authorization code service
    '''

    logger.info('mapcore_get_accesstoken started.')
    url = MAPCORE_HOSTNAME + MAPCORE_TOKEN_PATH
    basic_auth = (MAPCORE_CLIENTID, MAPCORE_SECRET)
    param = {
        'grant_type': 'authorization_code',
        'redirect_uri': redirect,
        'code': authcode
    }
    param = urllib.urlencode(param)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    }
    res = requests.post(url, data=param, headers=headers, auth=basic_auth, verify=VERIFY)
    res.raise_for_status()  # error check
    logger.info('mapcore_get_accesstoken response: ' + res.text)
    json = res.json()
    return (json['access_token'], json['refresh_token'])


# def mapcore_refresh_accesstoken(user, force=False):
#     '''
#     refresh access token with refresh token
#     :param user     OSFUser
#     :param force    falg to avoid availablity check
#     :return result 0..success, 1..must be login again, -1..any error
#     '''
#
#     logger.info('refuresh token for [' + user.eppn + '].')
#     url = MAPCORE_HOSTNAME + MAPCORE_TOKEN_PATH
#
#     # access token availability check
#     if not force:
#         param = {'access_token': user.map_profile.oauth_access_token}
#         headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
#         res = requests.post(url, data=param, headers=headers, verify=VERIFY)
#         if res.status_code == 200 and 'success' in res.json():
#             return 0  # notihng to do
#
#     # do refresh
#     basic_auth = (MAPCORE_CLIENTID, MAPCORE_SECRET)
#     param = {
#         'grant_type': 'refresh_token',
#         'refresh_token': user.map_profile.oauth_refresh_token
#     }
#     param = urllib.urlencode(param)
#     headers = {
#         'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
#     }
#     res = requests.post(url, data=param, headers=headers, auth=basic_auth, verify=VERIFY)
#     json = res.json()
#     if res.status_code != 200 or 'access_token' not in json:
#         return -1
#     logger.info('User [' + user.eppn + '] refresh access_token by [' + json['access_token'])
#
#     # update database
#     user.map_profile.oauth_access_token = json['access_token']
#     user.map_profile.oauth_refresh_token = json['refresh_token']
#     user.map_profile.oauth_refresh_time = timezone.now()
#     user.map_profile.save()
#     user.save()
#
#     return 0


def mapcore_remove_token(user):
    if user.map_profile is None:
        return
    user.map_profile.oauth_access_token = ''
    user.map_profile.oauth_refresh_token = ''
    user.map_profile.oauth_refresh_time = timezone.now()
    user.map_profile.save()


###
### sync functions
###

# ignore user.eppn=None
def query_contributors(node):
    return node.contributors.exclude(eppn=None)

# OSFuser essential feild keeper for comparing member
class RDMmember(object):
    def __init__(self, node, user):
        self.node = node
        self.user = user
        self.eppn = user.eppn        # ePPN
        self.user_id = user._id      # RDM internal user_id
        if node.has_permission(user, 'admin', check_parent=False):
            self.is_admin = True
            # self.access_token = user.map_profile.oauth_access_token
            # self.refresh_token = user.map_profile.oauth_refresh_token
        else:
            self.is_admin = False

    def is_admin(self):
        return self.is_admin


# compare member lists and apply  actions
def compare_members(rdm_members1, map_members1, to_map):
    rdm_members = sorted(rdm_members1, key=attrgetter('eppn'))
    map_members = sorted(map_members1, key=lambda x: x['eppn'])

    rdm_index = 0
    map_index = 0
    add = []
    delete = []
    upg = []
    downg = []
    while rdm_index < len(rdm_members) and map_index < len(map_members):
        logger.debug('compare_members: start: rdm_index={}, len(rdm_members)={}, map_index={}, len(map_members)={}'.format(rdm_index, len(rdm_members), map_index, len(map_members)))
        if map_members[map_index]['eppn'] == rdm_members[rdm_index].eppn:
            # exist in both -> check admin
            if rdm_members[rdm_index].is_admin:
                if map_members[map_index]['admin'] == 1 or map_members[map_index]['admin'] == 2:
                    # admin @ both
                    pass
                else:
                    # admin @ rdm only
                    if to_map:
                        upg.append(map_members[map_index])
                    else:
                        downg.append(rdm_members[rdm_index])
            else:
                if map_members[map_index]['admin'] == 1 or map_members[map_index]['admin'] == 2:
                    # admin in map only
                    if to_map:
                        downg.append(map_members[map_index])
                    else:
                        upg.append(rdm_members[rdm_index])
                else:
                    # regular @ both
                    pass
            rdm_index += 1
            map_index += 1

        elif map_members[map_index]['eppn'] < rdm_members[rdm_index].eppn:
            # exist in map only
            if to_map:
                delete.append(map_members[map_index])
            else:
                add.append(map_members[map_index])
            map_index += 1

        else:
            # exist in rdm only
            if to_map:
                add.append(rdm_members[rdm_index])
            else:
                delete.append(rdm_members[rdm_index])
            rdm_index += 1
    if to_map:
        while rdm_index < len(rdm_members):
            add.append(rdm_members[rdm_index])
            rdm_index += 1
        while map_index < len(map_members):
            delete.append(map_members[map_index])
            map_index += 1
    else:
        while map_index < len(map_members):
            add.append(map_members[map_index])
            map_index += 1
        while rdm_index < len(rdm_members):
            delete.append(rdm_members[rdm_index])
            rdm_index += 1

    logger.debug('compare_members: done: rdm_index={}, len(rdm_members)={}, map_index={}, len(map_members)={}'.format(rdm_index, len(rdm_members), map_index, len(map_members)))

    logger.debug('compare_members: result: to_map={}, add={}, delete={}, uprade={}, downgrade={}'.format(to_map, len(add), len(delete), len(upg), len(downg)))

    return add, delete, upg, downg
    # to_map:
    #   add: RDMmember,  delete: map_member, upg: map_member, downg: map_member
    # not to_map: (to RDM)
    #   add: map_member, delete: RDMmember,  upg: RDMmember,  downg: RDMmember


def is_node_admin(node, user):
    return node.has_permission(user, 'admin', check_parent=False)


def _mapcore_api_with_switching_token(access_user, node, group_key, func, **kwargs):
    candidates = []
    if access_user and access_user.eppn:
        candidates.append(access_user)  # top priority
    if node:
        if node.creator.eppn:
            candidates.append(node.creator)
        for contributor in query_contributors(node):
            candidates.append(contributor)
    if len(candidates) == 0:
        raise MAPCoreException(None, 'No user can use API of mAP Core.')

    # maintain the order and remove duplicated users
    first_e = None
    for candidate in sorted(set(candidates), key=candidates.index):
        if candidate.map_profile is None:
            continue
        try:
            mapcore = MAPCore(candidate)
            return func(mapcore, node, group_key, **kwargs)
        except MAPCoreException as e:
            if e.group_does_not_exist():
                raise
            if first_e is None:
                first_e = e
        except Exception as e:
            if first_e is None:
                first_e = e
    if first_e is None:
        first_e = Exception('No user have mAP access token')
    raise first_e   # missing original traceback

def _get_group_by_key(mapcore, node, group_key, **kwargs):
    return mapcore.get_group_by_key(group_key)

def _get_group_members(mapcore, node, group_key, **kwargs):
    return mapcore.get_group_members(group_key)

def _edit_group(mapcore, node, group_key, **kwargs):
    return mapcore.edit_group(group_key, node.title, node.description)

def _add_to_group(mapcore, node, group_key, **kwargs):
    return mapcore.add_to_group(group_key, kwargs['eppn'], kwargs['admin'])

def _remove_from_group(mapcore, node, group_key, **kwargs):
    return mapcore.remove_from_group(group_key, kwargs['eppn'])

def _edit_member(mapcore, node, group_key, **kwargs):
    return mapcore.edit_member(group_key, kwargs['eppn'], kwargs['admin'])

def mapcore_get_group_by_key(access_user, node, group_key):
    return _mapcore_api_with_switching_token(
        access_user, node, group_key, _get_group_by_key)

def mapcore_get_group_members(access_user, node, group_key):
    return _mapcore_api_with_switching_token(
        access_user, node, group_key, _get_group_members)

def mapcore_update_group(access_user, node, group_key):
    return _mapcore_api_with_switching_token(
        access_user, node, group_key, _edit_group)

def mapcore_add_to_group(access_user, node, group_key, eppn, admin):
    kwargs = {}
    kwargs['eppn'] = eppn
    kwargs['admin'] = admin
    return _mapcore_api_with_switching_token(
        access_user, node, group_key, _add_to_group, **kwargs)

def mapcore_remove_from_group(access_user, node, group_key, eppn):
    kwargs = {}
    kwargs['eppn'] = eppn
    return _mapcore_api_with_switching_token(
        access_user, node, group_key, _remove_from_group, **kwargs)

def mapcore_edit_member(access_user, node, group_key, eppn, admin):
    kwargs = {}
    kwargs['eppn'] = eppn
    kwargs['admin'] = admin
    return _mapcore_api_with_switching_token(
        access_user, node, group_key, _edit_member, **kwargs)

#
# functions for Web UI
#

# make mAP extended group info with members
def mapcore_get_extended_group_info(access_user, node, group_key, base_grp=None, can_abort=True):
    '''
    make mAP extended group info with members
    :param mapcore: MAPCore instance to access mAP core
    :param group_key: group_key of target mAP group
    :param base_grp: group info Dict when already have
    :param can_abort: True when allow exception, False when return status only
    :return: dict of extended group info
    # {
    #  "group_key": "c4e843f0-574f-11e9-9439-06df9add4f8a",
    #  "active": 1,
    #  "group_name": "TEST 0405 1206",
    #  "group_name_en": "Group Name",
    #  "introduction": "新規グループの紹介文。",
    #  "introduction_en": "This is an introduction message for the new group.",
    #  "public": 1,
    #  "inspect_join": メンバー参加条件 0=誰でも参加, 1=監視者の承諾が必要
    #  "open_member": メンバーの公開・非公開: 0=非公開、1=公開、2=参加者のみに公開
    #  "group_admin": [  <-- 名前は重複がありうるのでキーにならない
    #      "管理者の名前",
    #      "管理者の名前"
    #  ],
    #  "group_admin_eppn": [      <-- これが欲しい
    #      "管理者のeppn",
    #      "管理者のeppn"
    #  ],
    #  "group_member_list": [     <-- メンバーのリスト(管理者を探す)
    #   {
    #    "eppn": "test010@nii.ac.jp",
    #    "account_name": "hoge",
    #    "mail": "hoge@gmail.com",
    #    "admin": 2,
    #    "org_name": "boo",
    #    "university": "foo",
    #    "created_at": "2018-05-16 18:30:17",
    #    "modified_at": "2019-03-17 14:29:15"
    #   }, {...}, ...
    #  ],
    #  "created_at": "2019-04-05 12:06:12",
    #  "modified_at": "2019-04-05 12:07:09"
    # }
    '''

    try:
        group_ext = base_grp
        if base_grp is None:
            result = mapcore_get_group_by_key(access_user, node, group_key)
            group_ext = result['result']['groups'][0]
            #logger.debug('Group info:\n' + pp(group_ext))

        # get member list
        result = mapcore_get_group_members(access_user, node, group_ext['group_key'])
        member_list = result['result']['accounts']
        admins = []
        members = []
        for usr in member_list:
            if usr['admin'] == 2 or usr['admin'] == 1:
                usr['is_admin'] = True
                admins.append(usr['eppn'])
            else:
                usr['is_admin'] = False
            members.append(usr)

        group_ext['group_admin_eppn'] = admins
        group_ext['group_member_list'] = members
        #logger.debug('Member info:\n' + pp(members))
    except Exception:
        if can_abort:
            raise
        else:
            return False

    return group_ext

def mapcore_sync_map_new_group0(user, title):
    '''
    create new mAP group and return its group_key
    :param user:OSFUser  project creator aka mAP admin
    :param title:str group_name in mAP group
    :return: str: group_key
    '''

    logger.debug('crete mAP group with ePPN id [' + user.eppn + '].')

    # create mAP group
    mapcore = MAPCore(user)
    result = mapcore.create_group(title)
    group_key = result['result']['groups'][0]['group_key']
    #logger.debug('mAP group created:\n' + pp(result))

    return group_key

def mapcore_sync_map_new_group(user, title, use_raise=False):
    try:
        # for mock.patch()
        return mapcore_sync_map_new_group0(user, title)
    except Exception as e:
        logger.error('User(eppn={}) cannot create a new group(title={}) on mAP, reason={}'.format(user.eppn, utf8(title), utf8(str(e))))
        #TODO log
        if use_raise:
            raise
        else:
            return None


def mapcore_create_new_node_from_mapgroup(mapcore, map_group):
    '''
    create new Node from mAP group info
    :param map_group: dict: mAP group info by get_my_group
    :return: Node object or None at error
    '''

    logger.debug('mapcore_create_new_node_from_mapgroup({}, group_name={}) start'.format(mapcore.user.username, map_group['group_name']))
    # switch to admin user
    group_key = map_group['group_key']
    group_info_ext = mapcore_get_extended_group_info(mapcore.user, None, group_key, base_grp=map_group)

    logger.debug('mapcore_create_new_node_from_mapgroup({}, group_name={}) mapcore_get_extended_group_info done'.format(mapcore.user.username, map_group['group_name']))

    creator = None
    for admin_eppn in group_info_ext['group_admin_eppn']:
        try:
            user = OSFUser.objects.get(eppn=admin_eppn)
        except ObjectDoesNotExist:
            logger.info('mAP group [' + map_group['group_name'] + ']s admin [' + admin_eppn +
                        '] is not registerd in RDM')
            continue
        creator = user
        break

    if creator is None:
        msg = 'maAP group [' + map_group['group_name'] + '] has no RDM registerd admin user.'
        logger.error(msg)
        return None

    # create new RDM group
    node = Node(title=utf8dec(map_group['group_name']), creator=creator,
                is_public=True, category='project',
                map_group_key=group_key,
                description=utf8dec(group_info_ext['introduction']))
    node.map_group_key = group_key
    node.save()
    logger.info('New node [' + node.title + '] owned by [' + creator.eppn + '] is created.')
    return node


def mapcore_sync_rdm_project0(access_user, node, title_desc=False, contributors=False):
    '''
    mAP coreグループの情報をRDM Nodeに同期する
    :param node: Node object
    :param title_desc:  boolean that indicate group info sync
    :param contributors:  boolean that indicate contribuors
    :param mapcore:  MAPCore object to call mAP API with AccessCode in it
    :return: True on success, False on sync skip condition
    '''

    if node.is_deleted:
        return

    from framework.auth import Auth
    from osf.utils.permissions import CREATOR_PERMISSIONS, DEFAULT_CONTRIBUTOR_PERMISSIONS
    logger.debug('mapcore_sync_rdm_project0(' + node.title + ') start')

    try:
        locker.lock_node(node)
        # take mAP group info
        group_key = node.map_group_key
        map_group = mapcore_get_extended_group_info(access_user, node, group_key)

        # check conditions to sync
        if not map_group['active']:
            logger.info('mAP group [' + map_group['group_name'] + '] is not active, no sync')
            return False
        if not map_group['public']:
            logger.info('mAP group [' + map_group['group_name'] + '] is not public  no sync')
            return False
        if mapcore_group_member_is_private(map_group):
            # logger.error('mAP group [' + map_group['group_name'] + '] member list is not public  no sync')
            # return False
            logger.warning('mAP group({}) member list is private.'.format(map_group['group_name']))
            # TODO warning log

        # copy group info to rdm
        if title_desc:
            node.title = map_group['group_name']
            node.description = map_group['introduction']

        # sync members to rdm
        if contributors:
            # make contirbutor list
            rdm_member_list = []
            for rdm_user in query_contributors(node):
                rdm_member_list.append(RDMmember(node, rdm_user))
            map_member_list = map_group['group_member_list']
            add, delete, upg, downg = compare_members(rdm_member_list, map_member_list, False)
            #  add: map_member
            #  delete: RDMmember
            #  upg: RDMmember,
            #  downg: RDMmember

            # apply members to RDM
            for mapu in add:
                try:
                    rdmu = OSFUser.objects.get(eppn=mapu['eppn'])
                except Exception:
                    logger.info('mAP member [' + mapu['eppn'] + '] is not registed in RDM. (ignored)')
                    continue
                if mapu['is_admin']:
                    logger.info('mAP member [' + mapu['eppn'] + '] is registed as contributor ADMIN.')
                    node.add_contributor(rdmu, log=True, save=False, permissions=CREATOR_PERMISSIONS)
                else:
                    logger.info('mAP member [' + mapu['eppn'] + '] is registed as contributor MEMBER.')
                    node.add_contributor(rdmu, log=True, save=False, permissions=DEFAULT_CONTRIBUTOR_PERMISSIONS)
            for rdmu in delete:
                auth = Auth(user=rdmu.user)
                node.remove_contributor(rdmu.user, auth, log=True)
                logger.info('mAP member [' + rdmu.eppn + '] is remove from contributor')
            for rdmu in upg:
                if not is_node_admin(node, rdmu.user):
                    node.set_permissions(rdmu.user, CREATOR_PERMISSIONS, save=False)
                    logger.info('mAP member [' + rdmu.eppn + '] is upgrade to admin')
            for rdmu in downg:
                if is_node_admin(node, rdmu.user):
                    node.set_permissions(rdmu.user, DEFAULT_CONTRIBUTOR_PERMISSIONS, save=False)
                    logger.info('mAP member [' + rdmu.eppn + '] is downgrade to contributor membe')

        node.save()
    finally:
        locker.unlock_node(node)
    return True

def mapcore_sync_rdm_project(access_user, node, title_desc=False, contributors=False, use_raise=False):
    try:
        mapcore_sync_rdm_project0(access_user, node, title_desc=title_desc, contributors=contributors)
    except MAPCoreException as e:
        if e.group_does_not_exist():
            logger.info('RDM project [{} ({})] is deleted because linked mAP group does not exist.'.format(utf8(node.title), node._id))
            from framework.auth import Auth
            node.remove_node(Auth(user=node.creator))
        elif use_raise:
            raise

def mapcore_resign_map_group(node, user):
    '''
    RDM Prject から脱退した場合に、mAP グループから脱退する処理を行う
    :param node: Node: Project resigned
    :param user: OSFUser
    :return: None.  raise exception when error
    '''
    mapcore = MAPCore(user)
    return mapcore.remove_from_group(node.map_group_key, user.eppn)


def mapcore_sync_map_group1(access_user, node, title_desc=True, contributors=True):
    '''
    RDM Nodeの情報をmAPグループに同期する
    :param node: Node object
    :param title_desc:  boolean that indicate group info sync
    :param contributors:  boolean that indicate contribuors
    :param mapcore:  MAPCore object to call mAP API with AccessCode in it
    :return: True on success, False on sync skip condition
    '''

    logger.debug('mapcore_sync_map_group(\'' + node.title + '\') started.')

    # check Node attribute
    if node.is_deleted:
        logger.info('Node is deleted.  nothing to do.')
        return False

    try:
        locker.lock_node(node)
        group_key = node.map_group_key

        # sync group info
        if title_desc:
            mapcore_update_group(access_user, node, group_key)
            logger.info('Node title [' + node.title + '] and desctiption is sync to mAP group [' + group_key + '].')

        # sync members
        if contributors:
            rdm_members = []
            for member in query_contributors(node):
                rdmu = RDMmember(node, member)
                rdm_members.append(rdmu)
                # logger.debug('RDM contributor:\n' + pp(vars(rdmu)))

            map_group = mapcore_get_extended_group_info(access_user, node, group_key)
            map_members = map_group['group_member_list']
            #logger.debug('mAP group info:\n' + pp(map_group))
            #logger.debug('mAP group members: ' + pp(map_members))

            add, delete, upgrade, downgrade = compare_members(rdm_members, map_members, True)
            #  add: RDMmember,
            #  delete: map_member
            #  upgrade: map_member
            #  downgrade: map_member

            # apply members to mAP group
            for u in add:
                if u.is_admin:
                    admin = MAPCore.MODE_ADMIN
                else:
                    admin = MAPCore.MODE_MEMBER
                mapcore_add_to_group(access_user, node, group_key, u.eppn, admin)
                logger.info('mAP group [' + map_group['group_name'] + '] get new member [' + u.eppn + ']')
            for u in delete:
                eppn = u['eppn']
                try:
                    user = OSFUser.objects.get(eppn=eppn)
                except Exception:
                    logger.info('The user(eppn={}) does not exist in RDM. Do not remove the user from the mAP group({}).'.format(eppn, map_group['group_name']))
                    # TODO log?
                    user = None
                if user:
                    mapcore_remove_from_group(access_user, node, group_key, eppn)
                    logger.info('mAP group [' + map_group['group_name'] + ']s member [' + eppn + '] is removed')

            for u in upgrade:
                mapcore_edit_member(access_user, node, group_key, u['eppn'], MAPCore.MODE_ADMIN)
                logger.info('mAP group [' + map_group['group_name'] + ']s admin [' + u['eppn'] + '] is now a member')
            for u in downgrade:
                mapcore_edit_member(access_user, node, group_key, u['eppn'], MAPCore.MODE_MEMBER)
                logger.info('mAP group [' + map_group['group_name'] + ']s member [' + u['eppn'] + '] is now an admin')
    finally:
        locker.unlock_node(node)

    return True


def mapcore_sync_map_group0(access_user, node, title_desc=True, contributors=True):
    try:
        ret = mapcore_sync_map_group1(access_user, node, title_desc=title_desc, contributors=contributors)
    except Exception as e:
        logger.warning('The project({}) cannot be uploaded to mAP. (retry later), reason={}'.format(node._id, utf8(str(e))))
        # TODO log
        mapcore_set_standby_to_upload(node)  # retry later
        return
    if ret:
        mapcore_unset_standby_to_upload(node)
    return ret

def mapcore_sync_map_group(access_user, node, title_desc=True, contributors=True, use_raise=False):
    try:
        # for mock.patch()
        return mapcore_sync_map_group0(access_user, node, title_desc=title_desc, contributors=contributors)
    except Exception:
        if use_raise:
            raise
        # ignore error

def mapcore_url_is_my_projects(request_url):
    pages = ['dashboard', 'my_projects']

    for name in pages:
        if urlparse(request_url).path == urlparse(web_url_for(name)).path:
            return True
    return False

def mapcore_sync_rdm_my_projects0(user):
    '''
    RDMとmAPの両方にグループに所属:
       タイトルが変わっていない場合: なにもしない
       タイトルが変わっている場合: mAP側に反映またはRDM側に反映

    mAPグループだけに所属:
      対応するRDMにプロジェクトが存在:
        つまりcontributors不整合状態
        RDM側に反映 (mAP側に反映すべき情報がある場合はmAP側へ反映)
      対応するRプロジェクトがRDM側に無い:
        RDM側にプロジェクトを作成し、mAPグループから情報取得してRDM側に反映

    RDMプロジェクトだけに所属:
      group_keyがセットされていない:
        つまりまだmAP側と関連付けられていない
        プロジェクト画面遷移時にmAPグループを作成するので、何もしない
      mAPにグループが存在:
        つまりcontributors不整合状態
        RDM側に反映 (mAP側に反映すべき情報がある場合はmAP側へ反映)
      mAPにグループが無い:
        プロジェクトをis_deleted=Trueにする

    :param user: OSFUser
    :return: なし。エラー時には例外投げる

    '''

    logger.info('starting mapcore_sync_rdm_my_projects(\'' + user.eppn + '\').')

    try:
        locker.lock_user(user)

        my_rdm_projects = {}
        for project in Node.objects.filter(contributor__user__id=user.id):
            if project.map_group_key:
                my_rdm_projects[project.map_group_key] = project
            # if project.map_group_key is None:
            # ... This project will be synchronized in _view_project()

        mapcore = MAPCore(user)
        result = mapcore.get_my_groups()
        my_map_groups = {}
        for grp in result['result']['groups']:
            group_key = grp['group_key']
            my_map_groups[group_key] = grp

            if not grp['active'] or not grp['public']:
                logger.warning('mAP group [' + grp['group_name'] + '] has unsoutable attribute(s).  Ignore')
                continue
            if mapcore_group_member_is_private(grp):
                logger.warning('mAP group( {} ) member list is private. (skipped)'.format(grp['group_name']))
                continue
            logger.debug('mAP group [' + grp['group_name'] + '] (' + grp['group_key'] + ') is a candidate to Sync.')

            project_exists = False
            try:
                node = Node.objects.get(map_group_key=group_key)
                project_exists = True
                # exists in RDM and mAP
            except ObjectDoesNotExist as e:
                # exists only in mAP -> create new Node in RDM
                try:
                    node = mapcore_create_new_node_from_mapgroup(mapcore, grp)
                    if node is None:
                        logger.error('cannot create RDM project for mAP group [' + grp['group_name'] + '].  skip.')
                        #TODO log?
                        continue
                    logger.info('New node is created from mAP group [' + grp['group_name'] + '] (' + grp['group_key'] + ')')
                    # copy info and members to RDM
                    mapcore_sync_rdm_project(user, node,
                                             title_desc=True,
                                             contributors=True,
                                             use_raise=True)
                except MAPCoreException as e:
                    if e.group_does_not_exist():
                        # This group is not linked to this RDM SP.
                        # Other SPs may have the group.
                        del my_map_groups[group_key]
                        logger.info('The mAP group({}, group_key={}) exists but it is not linked to this RDM service provider.'.format(grp['group_name'], group_key))
                        # TODO log?
                    else:
                        logger.debug('MAPCoreException: {}'.format(utf8(str(e))))
                        raise

            if project_exists:
                # different contributors or title
                if my_rdm_projects.get(group_key) is None \
                   or node.title != utf8dec(grp['group_name']):
                    logger.debug('different contributors or title')
                    mapcore_sync_rdm_project_or_map_group(user, node)

        for group_key, project in my_rdm_projects.items():
            if project.is_deleted:
                logger.info('RDM project [{} ({})] was deleted. (skipped)'.format(
                    utf8(project.title), project._id))
                continue

            grp = my_map_groups.get(project.map_group_key)
            if grp:
                if project.title == utf8dec(grp['group_name']):
                    # already synchronized project
                    continue
                else:
                    logger.debug('different title')
                    mapcore_sync_rdm_project_or_map_group(user, project)
            else:
                # Project contributors is different from mAP group members.
                mapcore_sync_rdm_project_or_map_group(user, project)
    finally:
        locker.unlock_user(user)

    logger.debug('mapcore_sync_rdm_my_projects finished.')

def mapcore_sync_rdm_my_projects(user, use_raise=False):
    try:
        # for mock.patch()
        mapcore_sync_rdm_my_projects0(user)
    except Exception as e:
        logger.error('User(eppn={}) cannot compare my RDM Projects and my mAP groups, reason={}'.format(user.eppn, utf8(str(e))))
        if use_raise:
            raise


def mapcore_set_standby_to_upload(node):
    with transaction.atomic():
        n = Node.objects.select_for_update().get(guids___id=node._id)
        n.mapcore_standby_to_upload = timezone.now()
        n.save()
        logger.info('Project({}) will be uploaded to mAP (next time).'.format(node._id))
        logger.info('Project({}).mapcore_standby_to_upload={}'.format(node._id, n.mapcore_standby_to_upload))


def mapcore_is_on_standby_to_upload(node):
    with transaction.atomic():
        n = Node.objects.select_for_update().get(guids___id=node._id)
        return n.mapcore_standby_to_upload is not None

def mapcore_unset_standby_to_upload(node):
    with transaction.atomic():
        n = Node.objects.select_for_update().get(guids___id=node._id)
        n.mapcore_standby_to_upload = None
        n.save()
        logger.debug('Project({}).mapcore_standby_to_upload=None'.format(node._id))

SYNC_CACHE_TIME = 10  # sec.

def mapcore_set_sync_time(node):
    try:
        with transaction.atomic():
            n = Node.objects.select_for_update().get(guids___id=node._id)
            n.mapcore_sync_time = timezone.now()
            n.save()
    except Exception as e:
        logger.error('mapcore_set_sync_time: {}'.format(utf8(str(e))))
        # ignore

def mapcore_is_sync_time_expired(node):
    if node.mapcore_sync_time is None:
        return True
    if timezone.now() >= node.mapcore_sync_time + datetime.timedelta(seconds=SYNC_CACHE_TIME):
        logger.debug('mapcore_is_sync_time_expired: need sync')
        return True
    else:
        logger.debug('mapcore_is_sync_time_expired: skip sync')
        return False

def mapcore_sync_rdm_project_or_map_group0(access_user, node, use_raise=False):
    if node.is_deleted:
        return
    if not mapcore_is_sync_time_expired(node):
        return  # skipped

    if node.map_group_key is None:
        group_key = mapcore_sync_map_new_group(node.creator, node.title,
                                               use_raise=use_raise)
        if group_key:
            node.map_group_key = group_key
            node.save()
            mapcore_sync_map_group(access_user, node,
                                   title_desc=True, contributors=True,
                                   use_raise=use_raise)
    elif mapcore_is_on_standby_to_upload(node):
        mapcore_sync_map_group(access_user, node,
                               title_desc=True, contributors=True,
                               use_raise=use_raise)
    else:
        mapcore_sync_rdm_project(access_user, node,
                                 title_desc=True, contributors=True,
                                 use_raise=use_raise)
    mapcore_set_sync_time(node)

def mapcore_sync_rdm_project_or_map_group(access_user, node, use_raise=False):
    # for mock.patch()
    mapcore_sync_rdm_project_or_map_group0(access_user, node, use_raise=use_raise)

#
# debugging utilities
#

# add a contirbutor to a project
def add_contributor_to_project(node_name, eppn):
    from osf.utils.permissions import DEFAULT_CONTRIBUTOR_PERMISSIONS

    # get node object
    try:
        node = Node.objects.get(title=node_name)
    except Exception as e:
        print(type(e))
        print(e)
        return

    # get user object
    try:
        user = OSFUser.objects.get(eppn=eppn)
    except Exception as e:
        print(type(e))
        print(e)
        return

    # add user as contributor
    if node.is_contributor(user):
        print('user is already joind')
        return

    ret = node.add_contributor(user, log=True, save=False, permissions=DEFAULT_CONTRIBUTOR_PERMISSIONS)
    print('add_contoributor returns: ' + ret)
    return


sleep_sec = 10

def user_lock_test(user):
    try:
        locker.lock_user(user)
        print('User ePPN: ' + user.eppn + ' is locked.')
        print('locked: sleep {}'.format(sleep_sec))
        time.sleep(sleep_sec)
    except KeyboardInterrupt:
        print('interrupted!')
    except Exception:
        pass
    finally:
        locker.unlock_user(user)
    print('User ePPN: ' + user.eppn + ' is unlocked.')

def node_lock_test(node):
    try:
        locker.lock_node(node)
        print('Node (GUID=' + node._id + ') is locked.')
        print('locked: sleep {}'.format(sleep_sec))
        #time.sleep(sleep_sec)
        for i in range(sleep_sec):
            print('mapcore_api_locked={}'.format(
                Node.objects.get(guids___id=node._id).mapcore_api_locked))
            time.sleep(1)
    except KeyboardInterrupt:
        print('interrupted!')
    except Exception:
        pass
    finally:
        locker.unlock_node(node)
    print('Node (GUID=' + node._id + ') is unlocked.')

if __name__ == '__main__':
    print('In Main')

    if False:
        # API呼び出しの権限テスト
        me1 = OSFUser.objects.get(eppn=sys.argv[2])
        map1 = MAPCore(me1)
        me2 = OSFUser.objects.get(eppn=sys.argv[3])
        map2 = MAPCore(me2)
        me3 = OSFUser.objects.get(eppn=sys.argv[4])
        map3 = MAPCore(me3)

        try:
            res = map1.get_group_by_key(sys.argv[1])
            grp1 = res['result']['groups'][0]
            gk1 = grp1['group_key']
            print('Title [' + grp1['group_name'] + '], Key [' + grp1['group_key'] + '], by user [' + me1.eppn + ']')
            res = map1.get_group_members(gk1)
            for mem in res['result']['accounts']:
                print('ePPN [' + mem['eppn'] + '], Account [' + mem['account_name'] + ']')
        except Exception as e:
            print(e.message)

        try:
            res = map2.get_group_by_key(sys.argv[1])
            grp2 = res['result']['groups'][0]
            gk2 = grp2['group_key']
            print('Title [' + grp2['group_name'] + '], Key [' + grp2['group_key'] + '], by user [' + me2.eppn + ']')
            res = map2.get_group_members(gk2)
            for mem in res['result']['accounts']:
                print('ePPN [' + mem['eppn'] + '], Account [' + mem['account_name'] + ']')
        except Exception as e:
            print(e.message)

        try:
            res = map3.get_group_by_key(sys.argv[1])
            grp3 = res['result']['groups'][0]
            gk3 = grp3['group_key']
            print('Title [' + grp3['group_name'] + '], Key [' + grp3['group_key'] + '], by user [' + me3.eppn + ']')
            res = map3.get_group_members(gk3)
            for mem in res['result']['accounts']:
                print('ePPN [' + mem['eppn'] + '], Account [' + mem['account_name'] + ']')
        except Exception as e:
            print(e.message)

    if False:
        me = OSFUser.objects.get(eppn=sys.argv[1])
        mapcore = MAPCore(me)
        result = mapcore.get_my_groups()
        my_map_groups = {}
        for grp in result['result']['groups']:
            group_key = grp['group_key']
            print('mAP group [' + grp['group_name'] + '] has key [' + group_key + '].')
            try:
                json = mapcore.get_group_members(group_key)
            except Exception as e:
                print('Exception: ', type(e), e.message)
                continue
            print(pp(json))
        exit(0)

    if False:
        me = OSFUser.objects.get(eppn=sys.argv[1])
        mapcore_sync_rdm_my_projects(me)
        pass

    if False:
        me = OSFUser.objects.get(eppn=sys.argv[1])
        print('mapcore_api_is_available=' + str(mapcore_api_is_available(me)))

    if False:
        me = OSFUser.objects.get(eppn=sys.argv[1])
        mapcore = MAPCore(me)
        result = mapcore.get_my_groups()
        print('mapcore.get_my_groups=' + str(result))
        groups = result['result']['groups']
        for g in groups:
            group_key = g['group_key']  # + '__NOTFOUND'
            try:
                node = Node.objects.get(map_group_key=group_key)
            except Exception:
                continue
            print(group_key)
            try:
                ginfo = mapcore.get_group_by_key(group_key)
                print(str(ginfo))
            except MAPCoreException as e:
                print(e)
                print(e.group_does_not_exist())
            gext = mapcore_get_extended_group_info(me, node, group_key)
            print(str(gext))

    # RDM -> mAP project sync
    if False:
        print('RDM -> mAP sync test')
        node = Node.objects.get(title=sys.argv[1])
        user = OSFUser.objects.get(eppn=sys.argv[2])
        if node.map_group_key is None:
            group_key = mapcore_sync_map_new_group(user, node.title)
            node.map_group_key = group_key
            node.save()
        try:
            mapcore_sync_map_group(user, node)
        except Exception as e:
            print(e.message)

    if False:  # test for authcode request
        mapcore_request_authcode(next_url=sys.argv[1])

    if False:
        user = OSFUser.objects.get(eppn=sys.argv[1])
        node = Node.objects.get(title=sys.argv[2])
        eppn = sys.argv[3]
        #eppn = user.eppn
        mapcore_add_to_group(user, node, node.map_group_key, eppn, MAPCore.MODE_MEMBER)

    if True:
        me = OSFUser.objects.get(eppn=sys.argv[1])
        user_lock_test(me)

    if False:
        node = Node.objects.get(guids___id=sys.argv[1])
        node_lock_test(node)
