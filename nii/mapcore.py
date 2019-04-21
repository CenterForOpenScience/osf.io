# -*- coding: utf-8 -*-
# mAP core Group / Member syncronization


from datetime import datetime as dt
import logging
import os
import sys
import requests
import urllib
from operator import attrgetter
from pprint import pformat as pp

from urlparse import urlparse

from website import settings

# TODO import
map_hostname = settings.MAPCORE_HOSTNAME
map_authcode_path = settings.MAPCORE_AUTHCODE_PATH
map_token_path = settings.MAPCORE_TOKEN_PATH
map_refresh_path = settings.MAPCORE_REFRESH_PATH
map_clientid = settings.MAPCORE_CLIENTID
map_secret = settings.MAPCORE_SECRET
map_authcode_magic = settings.MAPCORE_AUTHCODE_MAGIC
my_home = settings.DOMAIN

logger = logging.getLogger(__name__)

# initialize for standalone exec
if __name__ == '__main__':
    logger.setLevel(level=logging.DEBUG)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    from website.app import init_app
    init_app(routes=False, set_backends=False)

from osf.models.user import OSFUser
from osf.models.node import Node
from osf.models.map import MAPProfile
from website.util import web_url_for
from nii.mapcore_api import (MAPCore, MAPCoreException, VERIFY,
                             MAPCORE_DEBUG, MAPCoreLogger,
                             mapcore_group_member_is_private)
from django.core.exceptions import ObjectDoesNotExist


if MAPCORE_DEBUG:
    logger = MAPCoreLogger(logger)


def mapcore_is_enabled():
    return True if map_clientid else False


# True or Exception
def mapcore_api_is_available(user):
    mapcore = MAPCore(user)
    mapcore.get_api_version()
    logger.debug('mapcore_api_is_available::Access Token (for {}) is up-to-date'.format(user.username))
    return True


def mapcore_log_error(msg):
    logger.error(msg)


def mapcore_request_authcode(**kwargs):
    '''
    get an authorization code from mAP. this process will redirect some times.
    :param params  dict of GET parameters in request
    '''

    # logger.info("enter mapcore_get_authcode.")
    # logger.info("MAPCORE_HOSTNAME: " + map_hostname)
    # logger.info("MAPCORE_AUTHCODE_PATH: " + map_authcode_path)
    # logger.info("MAPCORE_TOKEN_PATH: " + map_token_path)
    # logger.info("MAPCORE_REFRESH_PATH: " + map_refresh_path)
    # logger.info("MAPCORE_CLIENTID: " + map_clientid)
    # logger.info("MAPCORE_SECRET: " + map_secret)
    # logger.info("MAPCORE_REIRECT: " + map_redirect)

    # parameter check
    if 'request' in kwargs.keys():
        kwargs = kwargs['request']
    logger.debug('mapcore_request_authcode get params:\n')
    logger.debug(pp(kwargs))
    next_url = kwargs.get('next_url')
    if next_url is not None:
        state_str = next_url.encode('base64')
    else:
        state_str = map_authcode_magic

    # make call
    url = map_hostname + map_authcode_path
    redirect_uri = settings.DOMAIN + web_url_for('mapcore_oauth_complete')[1:]
    logger.info('mapcore_request_authcode: redirect_uri is [' + redirect_uri + ']')
    params = {'response_type': 'code',
              'redirect_uri': redirect_uri,
              'client_id': map_clientid,
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
    if isinstance(user, OSFUser):
        logger.info('in mapcore_receive_authcode, user is instance of OSFUser')
    else:
        logger.info('in mapcore_receive_authcode, user is NOT instance of OSFUser')

    logger.info('get an oatuh response:')
    s = ''
    for k, v in params.items():
        s += '(' + k + ',' + v + ') '
    logger.info('oauth returned parameters: ' + s)

    # authorization code check
    if 'code' not in params or 'state' not in params:
        raise ValueError('invalid response from oauth provider')

    # exchange autorization code to access token
    authcode = params['code']
    # authcode = 'AUTHORIZATIONCODESAMPLE'
    # eppn = 'foobar@esample.com'
    redirect_uri = settings.DOMAIN + web_url_for('mapcore_oauth_complete')[1:]
    (access_token, refresh_token) = mapcore_get_accesstoken(authcode, redirect_uri)

    # set mAP attribute into current user
    map_user, created = MAPProfile.objects.get_or_create(eppn=user.eppn)
    if created:
        logger.info('MAPprofile new record created for ' + user.eppn)
    map_user.oauth_access_token = access_token
    map_user.oauth_refresh_token = refresh_token
    map_user.oauth_refresh_time = dt.utcnow()
    user.map_profile = map_user
    map_user.save()
    logger.info('User [' + user.eppn + '] get access_token [' + access_token + '] -> saved')
    user.save()

    # DEBUG: read record and print
    """
    logger.info('In database:')
    me = OSFUser.objects.get(eppn=user.eppn)
    logger.info('name: ' + me.fullname)
    logger.info('eppn: ' + me.eppn)
    if hasattr(me, 'map_profile'):
        logger.info('access_token: ' + me.map_profile.oauth_access_token)
        logger.info('refresh_token: ' + me.map_profile.oauth_refresh_token)
    """

    if params['state'] != map_authcode_magic:
        return params['state'].decode('base64')  # user defined state string
    return my_home   # redirect to home -> will redirect to dashboard


def mapcore_get_accesstoken(authcode, redirect):
    '''
    exchange authorization code to access token and refresh token
    API call returns the JSON response from mAP authorization code service
    '''

    logger.info('mapcore_get_accesstoken started.')
    url = map_hostname + map_token_path
    basic_auth = (map_clientid, map_secret)
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


def mapcore_refresh_accesstoken(user, force=False):
    '''
    refresh access token with refresh token
    :param user     OSFUser
    :param force    falg to avoid availablity check
    :return resulut 0..success, 1..must be login again, -1..any error
    '''

    logger.info('refuresh token for [' + user.eppn + '].')
    url = map_hostname + map_token_path

    # access token availability check
    if not force:
        param = {'access_token': user.map_profile.oauth_access_token}
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
        res = requests.post(url, data=param, headers=headers, verify=VERIFY)
        if res.status_code == 200 and 'success' in res.json():
            return 0  # notihng to do

    # do refresh
    basic_auth = (map_clientid, map_secret)
    param = {
        'grant_type': 'refresh_token',
        'refresh_token': user.map_profile.oauth_refresh_token
    }
    param = urllib.urlencode(param)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    }
    res = requests.post(url, data=param, headers=headers, auth=basic_auth, verify=VERIFY)
    json = res.json()
    if res.status_code != 200 or 'access_token' not in json:
        return -1
    logger.info('User [' + user.eppn + '] refresh access_token by [' + json['access_token'])

    # update database
    user.map_profile.oauth_access_token = json['access_token']
    user.map_profile.oauth_refresh_token = json['refresh_token']
    user.map_profile.oauth_refresh_time = dt.utcnow()
    user.map_profile.save()
    user.save()

    return 0

###
### sync functions
###

# OSFuser essential feild keeper for comparing member
class RDMmember(object):
    def __init__(self, node, user):
        self.node = node
        self.user = user
        self.eppn = user.eppn        # ePPN
        self.user_id = user._id      # RDM internal user_id
        if node.has_permission(user, 'admin', check_parent=False):
            self.is_admin = True
            self.access_token = user.map_profile.oauth_access_token
            self.refresh_token = user.map_profile.oauth_refresh_token
        else:
            self.is_admin = False

    def is_admin(self):
        return self.is_admin


# compare member lists and apply  actions
def compare_members(rdm_members, map_members, to_map):
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


# def mapcore_users_map_groups(user):
#     '''
#     get mAP groups a user belongs to
#     :param user: OSFuser
#     :return:: extended group list that the user belongs to

#     '''

#     # get group list a GRDM user belogns to
#     mapcore = MAPCore(user)
#     result = mapcore.get_my_groups()
#     if result is False:
#         return
#     group_list = result['result']['groups']

#     # make a detailed group info list including members
#     group_info_list = []
#     for grp in group_list:
#         if grp['active'] == 0 or grp['public'] != 1 \
#            or mapcore_group_member_is_private(grp):
#             continue    # INACTIVE or CLOSED GROUP or CLOSED MEMBER
#         result = mapcore_get_extended_group_info(mapcore, grp['group_key'])
#         if result is False:
#             return False
#         group_info_list.append(result)
#     logger.debug('user [' + user.eppn + '] belongs group:\n' + pp(group_info_list))
#     return group_info_list


def is_node_admin(node, user):
    return node.has_permission(user, 'admin', check_parent=False)


# # sync mAP group to GRDM
# def mapcore_group_sync_to_rdm(map_group):
#     # TODO: mAPから削除されたことは検出できない。グループ同士の比較を行うのには、ユーザが所属するグループの抽出と総なめが必要
#     '''
#     sync group members mAP Group -> RDM Project
#     it will scan mAP groups which user belongs, and sync members to to GRDM
#     :param: map_group : dict for extened group
#     :return: rdm_group : created or updated GRDM Node object
#     '''
#     from framework.auth import Auth
#     from osf.utils.permissions import CREATOR_PERMISSIONS, DEFAULT_CONTRIBUTOR_PERMISSIONS

#     logger.info('mapcore_group_sync_to_rdm(\'' + map_group['group_name'] + '\') is started.')

#     # check conditions to sync
#     if not map_group['active']:
#         logger.info('mAP group [' + map_group['group_name'] + '] is not active  no sync')
#         return
#     if not map_group['public']:
#         logger.info('mAP group [' + map_group['group_name'] + '] is not public  no sync')
#         return
#     if map_group['open_member'] == 0:  # private
#         logger.info('mAP group [' + map_group['group_name'] + '] member list is not public  no sync')
#         return

#     # search existing GRDM project
#     node = None
#     node_candidate = None
#     rdm_candidates = Node.objects.filter(title=map_group['group_name'])
#     if rdm_candidates.count() > 0:
#         for rdm_proj in rdm_candidates:
#             logger.debug('RDM proj [' + rdm_proj.title + '] is a candidate to sync')
#             if rdm_proj.is_deleted:
#                 logger.info('RDM projet [' + rdm_proj.title + '] is deleted.')
#                 continue
#             if rdm_proj.map_group_key is not None:
#                 logger.debug('RDM proj [' + rdm_proj.title + '] has key [' + rdm_proj.map_group_key,
#                              '] and mAP group has [' + map_group['group_key'] + '.')
#                 if rdm_proj.map_group_key == map_group['group_key']:
#                     node = rdm_proj  # exactly match
#                     break
#             else:
#                 logger.info('Node [' + rdm_proj.title + '] doesn\'t have mAP group link.')
#                 if node_candidate is None:
#                     node_candidate = rdm_proj  # title match but has no key
#         if node is None:
#             node = node_candidate

#     # create new Node
#     if node is None:
#         # search candidate of creator accounts
#         owner = None
#         for admin_eppn in map_group['group_admin_eppn']:
#             try:
#                 adminu = OSFUser.objects.get(eppn=admin_eppn)
#             except Exception:
#                 logger.info('mAP group admin [' + admin_eppn + '] doesn\'t have account in GRDM.')
#                 continue
#             owner = adminu
#             break
#         if owner is None:
#             logger.warning('all of mAP group [' + map_group['group_name'] + '] admins doen\'t have account in GRDM')
#             return
#         logger.info('mAP group [' + map_group['group_name'] + '] admin [' + owner.eppn + '] is select to owner')

#         # create new GRDM Project
#         node = Node(title=map_group['group_name'], creator=owner,
#                     is_public=True, category='project',
#                     map_group_key=map_group['group_key'],
#                     description=map_group['introduction'])
#         node.save()

#     # make contirbutor list
#     rdm_member_list = []
#     if hasattr(node, 'contributors'):
#         for rdm_user in node.contributors.all():
#             rdm_member_list.append(RDMmember(node, rdm_user))

#     # compare members
#     rdm_member_list_s = sorted(rdm_member_list, key=attrgetter('eppn'))
#     map_member_list = sorted(map_group['group_member_list'], key=lambda x: x['eppn'])
#     add, delete, upg, downg = compare_members(rdm_member_list_s, map_member_list, False)
#     #   add: map_member, delete: RDMmember,  upg: RDMmember,  downg: RDMmember

#     # apply members to RDM
#     for mapu in add:
#         try:
#             rdmu = OSFUser.objects.get(eppn=mapu['eppn'])
#         except Exception:
#             logger.info('mAP member [' + mapu['eppn'] + '] is not registed in RDM.  Ignore')
#             continue
#         if mapu['is_admin']:
#             logger.info('mAP member [' + mapu['eppn'] + '] is registed as contributor ADMIN.')
#             node.add_contributor(rdmu, log=True, save=False, permissions=CREATOR_PERMISSIONS)
#         else:
#             logger.info('mAP member [' + mapu['eppn'] + '] is registed as contributor MEMBER.')
#             node.add_contributor(rdmu, log=True, save=False, permissions=DEFAULT_CONTRIBUTOR_PERMISSIONS)
#     for rdmu in delete:
#         auth = Auth(user=rdmu)
#         node.remove_contributor(rdmu, auth, log=True)
#         logger.info('mAP member [' + mapu['eppn'] + '] is remove from contributor')
#     for rdmu in upg:
#         if not is_node_admin(node, rdmu):
#             node.set_permission(rdmu, CREATOR_PERMISSIONS, safe=False)
#             logger.info('mAP member [' + mapu['eppn'] + '] is upgrade to admin')
#     for rdmu in downg:
#         if is_node_admin(node, rdmu):
#             node.set_permission(rdmu, DEFAULT_CONTRIBUTOR_PERMISSIONS, safe=False)
#             logger.info('mAP member [' + mapu['eppn'] + '] is downgrade to contributor membe')

#     # nodeをsaveする
#     node.save()
#     return node


# # sync GRDM group to mAP
# def mapcore_group_sync_to_map(node):
#     '''
#     sync group members RDM Project -> mAP Group
#     :param node  RDM Node object
#     '''

#     logger.info('mapcore_group_sync_to_map started for [' + node.title + ']')

#     # check Node attribute
#     if node.is_deleted:
#         logger.info('Node is deleted.  nothing to do.')
#         return

#     # get the RDM contributor and make lists
#     rdm_admin = []
#     rdm_members = []
#     for member in node.contributors.all():
#         rdmu = RDMmember(node, member)
#         rdm_members.append(rdmu)
#         if rdmu.is_admin:
#             rdm_admin.append(rdmu)
#         logger.debug('RDM contributor:\n' + pp(vars(rdmu)))
#     rdm_members.sort(key=attrgetter('eppn'))

#     # get admin privilaged tokens
#     if node.creator:
#         priv_user = node.creator
#     else:
#         if len(rdm_admin) == 0:
#             logger.warning('Node (' + node.title + ') has no admin.  cannot sync')
#             return
#         priv_user = rdm_admin[0]
#     mapcore = MAPCore(priv_user)
#     logger.info('group [' + node.title + '] sync with [' + priv_user.eppn + ']\'s AccessToken')

#     # already combined to mAP group or search by name
#     if node.map_group_key is not None:
#         logger.info('RDM group [' + node.title + '] is linked to mAP [' + node.map_group_key + '].')
#         map_group = mapcore_get_extended_group_info(mapcore, node.map_group_key)
#         if map_group is False:
#             return
#     else:
#         # create new group on mAP
#         # TODO: RDM may have multiple Project having same name
#         #  --> fix get_group_by_name to return multiple groups and select by CGGroup's group_key (may be)
#         result = mapcore.get_group_by_name(node.title)  # it returns 1 group only
#         if result is not False:
#             group_key = result['result']['groups'][0]['group_key']
#             map_group = mapcore_get_extended_group_info(mapcore, group_key)
#         else:
#             # create new mAP group
#             result = mapcore.create_group(node.title)
#             if result is False:
#                 logger.error('create_group('' + node.title + '') fail')
#                 return
#             map_group = result['result']['groups'][0]
#             group_key = map_group['group_key']
#             result = mapcore.edit_group(group_key, node.title, node.description)
#             if result is False:
#                 logger.error('edt_group(' + group_key + ', ' + node.title + ', ' + node.description + ') fail')
#                 return
#             map_group['group_admin_eppn'] = [priv_user.eppn]
#             map_group['group_member_list'] = []

#         node.map_group_key = map_group['group_name']
#         node.save()

#     logger.debug('mAP group info:\n' + pp(map_group))
#     map_members = map_group['group_member_list']
#     map_members.sort(key=lambda u: u['eppn'])

#     add, delete, upgrade, downgrade = compare_members(rdm_members, map_members, True)
#     #   add: RDMmember,  delete: map_member, upgrade: map_member, downgrade: map_member

#     # apply members to mAP group
#     for u in add:
#         if u.is_admin:
#             admin = MAPCore.MODE_ADMIN
#         else:
#             admin = MAPCore.MODE_MEMBER
#         result = mapcore.add_to_group(group_key, u.eppn, admin)
#         if result is False:
#             return  # error reason is logged by API call
#         logger.info('mAP group [' + map_group['group_name'] + '] get new member [' + u.eppn + ']')
#     for u in delete:
#         result = mapcore.remove_from_group(group_key, u.eppn)
#         if result is False:
#             return  # error reason is logged by API call
#         logger.info('mAP group [' + map_group['group_name'] + ']s member [' + u.eppn + '] is removed')
#     for u in upgrade:
#         result = mapcore.edit_member(group_key, u.eppn, mapcore.MODE_ADMIN)
#         if result is False:
#             return  # error reason is logged by API call
#         logger.info('mAP group [' + map_group['group_name'] + ']s admin [' + u.eppn + '] is now a member')
#     for u in downgrade:
#         result = mapcore.edit_member(group_key, u.eppn, mapcore.MODE_MEMBER)
#         if result is False:
#             return  # error reason is logged by API call
#         logger.info('mAP group [' + map_group['group_name'] + ']s member [' + u.eppn + '] is now an admin')

#     return


#
# functions for Web UI
#

class MAPCoreUserInfoException(MAPCoreException):
    def __init__(self, msg, type='UNKNOWN'):
        ext_message = '{} (type={})'.format(msg, type)
        super(MAPCoreUserInfoException, self).__init__(None, ext_message)

# make mAP extended group info with members
def mapcore_get_extended_group_info(mapcore, group_key, can_abort=True):
    '''
    make mAP extended group info with members
    :param mapcore: MAPCore instance to access mAP core
    :param group_key: group_key of target mAP group
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

    result = mapcore.get_group_by_key(group_key)
    group_ext = result['result']['groups'][0]
    #logger.debug('Group info:\n' + pp(group_ext))

    # if mapcore_group_member_is_private(group_ext):
    #     msg = 'mAP group [' + group_ext['group_name'] + '] has CLOSED_MEMBER setting.'
    #     logger.error(msg)
    #     if can_abort:
    #         raise MAPCoreUserInfoException(msg, 'MapGroupSetting')
    #     else:
    #         return False

    # get member list
    result = mapcore.get_group_members(group_ext['group_key'])
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

    return group_ext


def mapcore_sync_map_new_group(user, title):
    '''
    create new mAP group and return its group_key
    :param user:OSFUser  project creator aka mAP admin
    :param title:str group_name in mAP group
    :return: str: group_key
    '''

    logger.debug('crete mAP group with ePPN id [' + user.eppn + '].')

    # create mAP group
    map = MAPCore(user)
    result = map.create_group(title)
    group_key = result['result']['groups'][0]['group_key']
    #logger.debug('mAP group created:\n' + pp(result))

    # set attributes in craete_group()
    #result = map.edit_group(group_key, title, title)  # it sets PUBLIC ACTIVE OPENMEMBER:1
    #logger.debug('mAP group created\n' + pp(result))

    return group_key


def mapcore_get_group_detail_info(mapcore, group_key):
    '''
    get details for the group
    :param mapcore: MAPCoreインスタンス
    :param group_key: group_key
    :return: mAPグループ情報のdict
    '''
    result = mapcore.get_group_by_key(group_key)
    if result is False:
        return False
    group_ext = result['result']['groups'][0]
    #logger.debug('Group info:\n' + pp(group_ext))
    return group_ext


def mapcore_create_new_node_from_mapgroup(mapcore, map_group):
    '''
    create new Node from mAP group info
    :param map_group: dict: mAP group info by get_my_group
    :return: Node object or None at error
    '''

    # switch to admin user
    group_key = map_group['group_key']
    group_info_ext = mapcore_get_extended_group_info(mapcore, group_key, can_abort=False)
    if group_info_ext is False:
        return None

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
    node = Node(title=map_group['group_name'], creator=creator,
                is_public=True, category='project',
                map_group_key=group_key,
                description=group_info_ext['introduction'])
    node.map_group_key = group_key
    node.save()
    logger.info('New node [' + node.title + '] owned by [' + creator.eppn + '] is created.')
    return node


#TODO mapcore -> access_user
def mapcore_sync_rdm_project(node, title_desc=False, contributors=False, mapcore=None):
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
    logger.debug('mapcore_sync_rdm_project(' + node.title + ') start')

    # take mAP group info
    group_key = node.map_group_key
    if mapcore is None:
        mapcore = MAPCore(node.creator)
    map_group = mapcore_get_extended_group_info(mapcore, group_key)

    # check conditions to sync
    if not map_group['active']:
        logger.error('mAP group [' + map_group['group_name'] + '] is not active, no sync')
        return False
    if not map_group['public']:
        logger.error('mAP group [' + map_group['group_name'] + '] is not public  no sync')
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
        for rdm_user in node.contributors.all():
            rdm_member_list.append(RDMmember(node, rdm_user))

        # compare members
        rdm_member_list_s = sorted(rdm_member_list, key=attrgetter('eppn'))
        map_member_list = sorted(map_group['group_member_list'], key=lambda x: x['eppn'])
        add, delete, upg, downg = compare_members(rdm_member_list_s, map_member_list, False)
        #   add: map_member, delete: RDMmember,  upg: RDMmember,  downg: RDMmember

        # apply members to RDM
        for mapu in add:
            try:
                rdmu = OSFUser.objects.get(eppn=mapu['eppn'])
            except Exception:
                logger.info('mAP member [' + mapu['eppn'] + '] is not registed in RDM.  Ignore')
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
    return True


def mapcore_resign_map_group(node, user):
    '''
    RDM Prject から脱退した場合に、mAP グループから脱退する処理を行う
    :param node: Node: Project resigned
    :param user: OSFUser
    :return: None.  raise exception when error
    '''
    mapcore = MAPCore(user)
    return mapcore.remove_from_group(node.map_group_key, user.eppn)


#TODO mapcore -> access_user
def _mapcore_sync_map_group(node, title_desc=True, contributors=True, mapcore=None):
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

    # get the RDM contributor and make lists
    #rdm_admin = []
    rdm_members = []
    for member in node.contributors.all():
        rdmu = RDMmember(node, member)
        rdm_members.append(rdmu)
        # if rdmu.is_admin:
        #    rdm_admin.append(rdmu)
        logger.debug('RDM contributor:\n' + pp(vars(rdmu)))

    rdm_members.sort(key=attrgetter('eppn'))

    # TODO retry by node.contributors
    # get admin privilaged tokens
    if mapcore is None:
        mapcore = MAPCore(node.creator)
    logger.debug('group [' + node.title + '] sync with [' + node.creator.eppn + ']\'s AccessToken')

    # get mAP group
    group_key = node.map_group_key
    map_group = mapcore_get_extended_group_info(mapcore, group_key)
    map_members = map_group['group_member_list']
    map_members.sort(key=lambda u: u['eppn'])
    # logger.debug('mAP group info:\n' + pp(map_group))
    logger.debug('mAP group members: ' + pp(map_members))

    # sync group info
    if title_desc:
        mapcore.edit_group(group_key, node.title, node.description)
        logger.info('Node title [' + node.title + '] and desctiption is sync to mAP group [' + group_key + '].')

    # sync members
    if contributors:
        # compare members
        add, delete, upgrade, downgrade = compare_members(rdm_members, map_members, True)
        #   add: RDMmember,  delete: map_member, upgrade: map_member, downgrade: map_member

        # apply members to mAP group
        for u in add:
            if u.is_admin:
                admin = MAPCore.MODE_ADMIN
            else:
                admin = MAPCore.MODE_MEMBER
            mapcore.add_to_group(group_key, u.eppn, admin)
            logger.info('mAP group [' + map_group['group_name'] + '] get new member [' + u.eppn + ']')
            #TODO log
        for u in delete:
            mapcore.remove_from_group(group_key, u['eppn'])
            logger.info('mAP group [' + map_group['group_name'] + ']s member [' + u['eppn'] + '] is removed')
            #TODO log
        for u in upgrade:
            mapcore.edit_member(group_key, u['eppn'], mapcore.MODE_ADMIN)
            logger.info('mAP group [' + map_group['group_name'] + ']s admin [' + u['eppn'] + '] is now a member')
            #TODO log
        for u in downgrade:
            mapcore.edit_member(group_key, u['eppn'], mapcore.MODE_MEMBER)
            logger.info('mAP group [' + map_group['group_name'] + ']s member [' + u['eppn'] + '] is now an admin')
            #TODO log

    return True


def mapcore_sync_map_group(node, title_desc=True, contributors=True, mapcore=None):
    if not mapcore_is_enabled():
        return False

    try:
        ret = _mapcore_sync_map_group(node, title_desc=title_desc, contributors=contributors, mapcore=mapcore)
        pass
    except Exception as e:
        logger.warning('The project ({}) cannot synchronize to mAP. (retry later): reason={}'.format(node._id, str(e)))
        # TODO log
        mapcore_set_standby_to_upload(node)  # retry later
        # Do not raise
        raise e
        #return False
    if ret:
        mapcore_unset_standby_to_upload(node)
    return ret

def mapcore_url_is_sync_target(request_url):
    pages = ['dashboard', 'my_projects']

    for name in pages:
        if urlparse(request_url).path == urlparse(web_url_for(name)).path:
            return True
    return False

def mapcore_member_list_is_accessible(access_user, node):
    try:
        mapcore = MAPCore(access_user)
        mapcore.get_group_members(node.map_group_key)
        return True
    except MAPCoreException as e:
        if e.listing_group_member_is_not_permitted():
            return False
        raise e

def mapcore_get_accessible_user(access_user, node):
    if mapcore_member_list_is_accessible(access_user, node):
        return access_user
    if mapcore_member_list_is_accessible(node.creator, node):
        return node.creator
    for contributor in node.contributors.all():
        if access_user != contributor and node.creator != contributor:
            if mapcore_member_list_is_accessible(contributor, node):
                return contributor
    return None


def mapcore_sync_rdm_user_projects(user, rdm2map=True):
    '''
    RDMとmAPの両方にグループに所属:
       タイトルが変わっていない場合: なにもしない
       タイトルが変わっている場合: mAP側に反映またはRDM側に反映

    mAPグループだけに所属:
      対応するRDMにプロジェクトが存在:
        つまりconributors不整合状態
        RDM側に反映 (mAP側に反映すべき情報がある場合はmAP側へ反映)
      対応するRDMにプロジェクトが無い:
        RDMにプロジェクトを作成し、mAPグループから情報取得してRDM側に反映

    RDMプロジェクトだけに所属:
      group_keyがセットされていない:
        つまりまだmAP側と関連付けられていない
        プロジェクト画面遷移時にmAPグループを作成するので、何もしない
      mAPにグループが存在:
        つまりconributors不整合状態
        RDM側に反映 (mAP側に反映すべき情報がある場合はmAP側へ反映)
      mAPにグループが無い:
        プロジェクトをis_deleted=Trueにする

    :param user: OSFUser
    :param rdm2map: boolean  enable RDM->mAP sync (mAP->RDM sync is always enable) (not implemented)
    :return: なし。エラー時には例外投げる

    '''

    logger.info('starting mapcore_sync_rdm_user_projects(\'' + user.eppn + '\').')

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
        #grp2 = mapcore.get_group_by_key(group_key)['result']['groups'][0]  # unnecessary
        grp2 = grp
        my_map_groups[group_key] = grp2

        if not grp2['active'] or not grp2['public']:
            logger.warning('mAP group [' + grp['group_name'] + '] has unsoutable attribute(s).  Ignore')
            continue
        if mapcore_group_member_is_private(grp2):
            logger.warning('mAP group({}) member list is private. (skipped)'.format(grp2['group_name']))
            continue

        new_project = False
        try:
            node = Node.objects.get(map_group_key=group_key)
            # exists in RDM and mAP
        except ObjectDoesNotExist as e:
            # exists only in mAP -> create new Node in RDM
            try:
                node = mapcore_create_new_node_from_mapgroup(mapcore, grp2)
                if node is None:
                    logger.error('cannot create RDM project for mAP group [' + grp['group_name'] + '].  skip.')
                    #TODO log?
                    continue
                new_project = True
                # copy info and members to RDM
                mapcore_sync_rdm_project(node, title_desc=True,
                                         contributors=True, mapcore=mapcore)
            except MAPCoreException as e:
                if e.group_does_not_exist():
                    # This group is not linked to this RDM SP.
                    # Other SPs may have the group.
                    del my_map_groups[group_key]
                else:
                    raise e

        if new_project is False:
            # different contributors or title
            if my_rdm_projects.get(group_key) is None \
               or node.title != grp2['group_name']:
                mapcore_sync_rdm_project_or_map_group(user, node)

    for group_key, project in my_rdm_projects.items():
        if project.is_deleted:
            logger.info('RDM project [{} ({})] is deleted. (skipped)'.format(
                project.title, project._id))
            continue

        try:
            grp = my_map_groups.get(project.map_group_key)
            if grp:
                if project.title != grp['group_name']:
                    mapcore_sync_rdm_project_or_map_group(user, project)
                # else: already synchronized project
                continue

            # Project contributors is different from mAP group members.
            #TODO retry in mapcore_get_extended_group_info()
            accessible_user = mapcore_get_accessible_user(user, project)
            mapcore_sync_rdm_project_or_map_group(accessible_user, project)
        except MAPCoreException as e:
            if e.group_does_not_exist():
                logger.info('RDM project [{} ({})] is deleted because linked mAP group does not exist.'.format(project.title, project._id))
                project.is_deleted = True
                project.save()

    logger.debug('mapcore_sync_rdm_user_projects finished.')


READY_SYNC_FILE_TMPL = '/code_src/tmp/rdm_mapcore_ready_to_sync_{}'  # TODO do not use

def mapcore_set_standby_to_upload(node):
    # TODO node.mapcore_standby_to_upload = dt.utcnow()
    # TODO node.save()
    # TODO MAPCORE_STANDBY_TO_UPLOAD_TIMEOUT = 5 min.
    filename = READY_SYNC_FILE_TMPL.format(node._id)  # use Guid
    try:
        with open(filename, 'w'):
            pass
    except OSError as e:
        # raise MAPCoreException(None, str(e))
        # TODO log
        logger.error('The project ({}) cannot synchronize to mAP. reason={}'.format(node._id, str(e)))


def mapcore_is_on_standby_to_upload(node):
    filename = READY_SYNC_FILE_TMPL.format(node._id)  # use Guid
    return os.path.exists(filename)


def mapcore_unset_standby_to_upload(node):
    filename = READY_SYNC_FILE_TMPL.format(node._id)  # use Guid
    try:
        return os.remove(filename)
    except OSError as e:
        import errno
        if e.errno != errno.ENOENT:
            # raise MAPCoreException(None, str(e))
            # TODO log
            logger.error('FATAL: {} cannot be deleted.'.format(filename))
            logger.error('The project ({}) cannot synchronize from mAP after this.'.format(node._id))


def mapcore_sync_rdm_project_or_map_group(access_user, node):
    if node.is_deleted:
        return
    if node.map_group_key is None:
        group_key = mapcore_sync_map_new_group(node.creator, node.title)
        node.map_group_key = group_key
        node.save()
        mapcore_sync_map_group(node, title_desc=True, contributors=True)
    elif mapcore_is_on_standby_to_upload(node):
        mapcore_sync_map_group(node, title_desc=True, contributors=True)
    else:
        mapcore_sync_rdm_project(node, title_desc=True, contributors=True,
                                 mapcore=MAPCore(access_user))


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


if __name__ == '__main__':
    print('In Main')

    if False:
        me = OSFUser.objects.get(eppn=sys.argv[1])
        print('mapcore_api_is_available=' + str(mapcore_api_is_available(me)))

    if True:
        me = OSFUser.objects.get(eppn=sys.argv[1])
        mapcore = MAPCore(me)
        result = mapcore.get_my_groups()
        print('mapcore.get_my_groups=' + str(result))
        groups = result['result']['groups']
        for g in groups:
            group_key = g['group_key']  # + '__NOTFOUND'
            print(group_key)
            try:
                ginfo = mapcore.get_group_by_key(group_key)
                print(str(ginfo))
            except MAPCoreException as e:
                print(e)
                print(e.group_does_not_exist())
            gext = mapcore_get_extended_group_info(mapcore, group_key)
            print(str(gext))

    # manual add contributor
    if False:
        add_contributor_to_project('Nagahara Test 001', 'hnagahara@openidp.nii.ac.jp')
        pass

    # mAP -> RDM group sync
    if False:
        print('Sync from user belonging.')
        me = OSFUser.objects.get(eppn=sys.argv[1])
        mapcore_sync_rdm_user_projects(me, rdm2map=False)

    # RDM -> mAP project sync
    if False:
        print('RDM -> mAP sync test')
        user = OSFUser.objects.get(eppn='nagahara@openidp.nii.ac.jp')
        node = Node.objects.get(title=sys.argv[1])
        if node.map_group_key is None:
            group_key = mapcore_sync_map_new_group(user, node.title)
            node.map_group_key = group_key
            node.save()
        try:
            mapcore_sync_map_group(node)
        except Exception as e:
            print(e.message)

    if False:  # get mAP group and members -> RDM
        me = OSFUser.objects.get(eppn=sys.argv[1])
        # mapcore_refresh_accesstoken(me)  # token refresh
        # print('name:', me.fullname)
        # print('eppn:', me.eppn)
        #if hasattr(me, 'map_profile'):
        #    print('access_token:', me.map_profile.oauth_access_token)
        #    print('refresh_token:', me.map_profile.oauth_refresh_token)
        #group_list = mapcore_users_map_groups(me)
        #mapcore_group_sync_to_rdm(group_list[1])

        # for group in group_list:
        #    mapcore_group_sync_to_rdm(group)

    if False:  # get RDM conributors and copy to mAP
        # owner = OSFUser.objects.get(eppn='hnagahara@openidp.nii.ac.jp')
        # mapcore_refresh_accesstoken(owner)  # token refresh
        node = Node.objects.get(title=sys.argv[1])
        #mapcore_group_sync_to_map(node)

    if False:  # test for authcode request
        mapcore_request_authcode(next_url=sys.argv[1])
