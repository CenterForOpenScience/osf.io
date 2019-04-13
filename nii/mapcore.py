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

from website import settings

map_hostname = settings.MAPCORE_HOSTNAME
map_authcode_path = settings.MAPCORE_AUTHCODE_PATH
map_token_path = settings.MAPCORE_TOKEN_PATH
map_refresh_path = settings.MAPCORE_REFRESH_PATH
map_clientid = settings.MAPCORE_CLIENTID
map_secret = settings.MAPCORE_SECRET
map_authcode_magic = settings.MAPCORE_AUTHCODE_MAGIC
my_home = settings.DOMAIN

# global setting
logger = logging.getLogger(__name__)
if __name__ == '__main__':
    logger = logging.getLogger('nii.mapcore')
    # stdout = logging.StreamHandler()  # log to stdio
    # logger.addHandler(stdout)
    logger.setLevel(level=logging.DEBUG)

    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    from website.app import init_app
    init_app(routes=False, set_backends=False)

from osf.models.user import OSFUser
from osf.models.node import Node
from osf.models.map import MAPProfile
from website.util import web_url_for
from nii.mapcore_api import MAPCore

def mapcore_is_enabled():
    if map_clientid == '':
        return False
    return True

def mapcore_api_is_available(user):

    mapcore = MAPCore(user)
    return mapcore.get_api_version()

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
        state_str = map_secret

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

    if params['state'] != map_secret:
        return params['state'].decode('base64')  # user defined state string
    return my_home   # redirect to home -> will redirect to dashboard


def mapcore_get_accesstoken(authcode, redirect, clientid=map_clientid, secret=map_secret):
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
    res = requests.post(url, data=param, headers=headers, auth=basic_auth)
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
        res = requests.post(url, data=param, headers=headers)
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
    res = requests.post(url, data=param, headers=headers, auth=basic_auth)
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
class RDMmember:
    def __init__(self, node, user):
        self.eppn = user.eppn        # ePPN
        self.user_id = user._id      # RDM internal user_id
        if node.has_permission(user, 'admin', check_parent=False):
            self.is_admin = True
            self.access_token = user.map_profile.oauth_access_token
            self.refresh_token = user.map_profile.oauth_refresh_time
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
    while to_map and rdm_index < len(rdm_members):
        add.append(rdm_members[rdm_index])
        rdm_index += 1
    while not to_map and map_index < len(map_members):
        add.append(map_members[map_index])
        map_index += 1

    return add, delete, upg, downg
    # to_map:
    #   add: RDMmember,  delete: map_member, upg: map_member, downg: map_member
    # not to_map: (to RDM)
    #   add: map_member, delete: RDMmember,  upg: RDMmember,  downg: RDMmember


# make mAP extended group info with members
def mapcore_get_extended_group_info(mapcore, group_key):
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
    #  "inspect_join": メンバー参加条件 0..誰でも参加, 1..監視者の承諾が必要
    #  "open_member": メンバーの公開・非公開 0..非公開、1..公開、2..参加者のみに公開
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
    if result is False:
        return False
    group_ext = result['result']['groups'][0]
    logger.debug('Group info:\n' + pp(group_ext))
    if group_ext['open_member'] == 0:
        logger.info('mAP group [' + group_ext['group_name'] + '] has CLOSED_MEMBER setting.  ignore.')
        return False

    # get member list
    result = mapcore.get_group_members(group_ext['group_key'])
    if result is False:
        return False
    member_list = result['result']['accounts']
    admins = []
    members = []
    for usr in member_list:
        if 'eppn' not in usr:
            logger.info('mAP user [' + usr['account_name'] + '] has no ePPN!  ignore')
            continue
        if usr['admin'] == 2 or usr['admin'] == 1:
            usr['is_admin'] = True
            admins.append(usr['eppn'])
        else:
            usr['is_admin'] = False
        members.append(usr)

    group_ext['group_admin_eppn'] = admins
    group_ext['group_member_list'] = members
    logger.debug('Member info:\n' + pp(members))

    return group_ext


def mapcore_users_map_groups(user):
    '''
    get mAP groups a user belongs to
    :param user: OSFuser
    :return:: extended group list that the user belongs to

    '''

    # get group list a GRDM user belogns to
    mapcore = MAPCore(user)
    result = mapcore.get_my_groups()
    if result is False:
        return
    group_list = result['result']['groups']

    # make a detailed group info list including members
    group_info_list = []
    for grp in group_list:
        if grp['active'] == 0 or grp['public'] != 1 or grp['open_member'] == 0:
            continue    # INACTIVE or CLOSED group, MEMBER_CLOSED
        result = mapcore_get_extended_group_info(mapcore, grp['group_key'])
        if result is False:
            return False
        group_info_list.append(result)
    logger.debug('user [' + user.eppn + '] belongs group:\n' + pp(group_info_list))
    return group_info_list


def is_node_admin(node, user):
    return node.has_permission(user, 'admin', check_parent=False)


# sync mAP group to GRDM
def mapcore_group_sync_to_rdm(map_group):
    # TODO: mAPから削除されたことは検出できない。グループ同士の比較を行うのには、ユーザが所属するグループの抽出と総なめが必要
    '''
    sync group members mAP Group -> RDM Project
    it will scan mAP groups which user belongs, and sync members to to GRDM
    :param: map_group : dict for extened group
    :return: rdm_group : created or updated GRDM Node object
    '''
    from framework.auth import Auth
    from osf.utils.permissions import CREATOR_PERMISSIONS, DEFAULT_CONTRIBUTOR_PERMISSIONS

    logger.info('mapcore_group_sync_to_rdm(\'' + map_group['group_name'] + '\') is started.')

    # check conditions to sync
    if not map_group['active']:
        logger.info('mAP group [' + map_group['group_name'] + '] is not active  no sync')
        return
    if not map_group['public']:
        logger.info('mAP group [' + map_group['group_name'] + '] is not public  no sync')
        return
    if map_group['open_member'] == 0:  # private
        logger.info('mAP group [' + map_group['group_name'] + '] member list is not public  no sync')
        return

    # search existing GRDM project
    node = None
    node_candidate = None
    rdm_candidates = Node.objects.filter(title=map_group['group_name'])
    if rdm_candidates.count() > 0:
        for rdm_proj in rdm_candidates:
            logger.debug('RDM proj [' + rdm_proj.title + '] is a candidate to sync')
            if rdm_proj.is_deleted:
                logger.info('RDM projet [' + rdm_proj.title + '] is deleted.')
                continue
            if rdm_proj.map_group_key is not None:
                logger.debug('RDM proj [' + rdm_proj.title + '] has key [' + rdm_proj.map_group_key,
                             '] and mAP group has [' + map_group['group_key'] + '.')
                if rdm_proj.map_group_key == map_group['group_key']:
                    node = rdm_proj  # exactly match
                    break
            else:
                logger.info('Node [' + rdm_proj.title + '] doesn\'t have mAP group link.')
                if node_candidate is None:
                    node_candidate = rdm_proj  # title match but has no key
        if node is None:
            node = node_candidate

    # create new Node
    if node is None:
        # search candidate of creator accounts
        owner = None
        for admin_eppn in map_group['group_admin_eppn']:
            try:
                adminu = OSFUser.objects.get(eppn=admin_eppn)
            except Exception:
                logger.info('mAP group admin [' + admin_eppn + '] doesn\'t have account in GRDM.')
                continue
            owner = adminu
            break
        if owner is None:
            logger.warn('all of mAP group [' + map_group['group_name'] + '] admins doen\'t have account in GRDM')
            return
        logger.info('mAP group [' + map_group['group_name'] + '] admin [' + owner.eppn + '] is select to owner')

        # create new GRDM Project
        node = Node(title=map_group['group_name'], creator=owner,
                    is_public=True, category='project',
                    map_group_key=map_group['group_key'],
                    description=map_group['introduction'])
        node.save()

    # make contirbutor list
    rdm_member_list = []
    if hasattr(node, 'contributors'):
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
        auth = Auth(user=rdmu)
        node.remove_contributor(rdmu, auth, log=True)
        logger.info('mAP member [' + mapu['eppn'] + '] is remove from contributor')
    for rdmu in upg:
        if not is_node_admin(node, rdmu):
            node.set_permission(rdmu, CREATOR_PERMISSIONS, safe=False)
            logger.info('mAP member [' + mapu['eppn'] + '] is upgrade to admin')
    for rdmu in downg:
        if is_node_admin(node, rdmu):
            node.set_permission(rdmu, DEFAULT_CONTRIBUTOR_PERMISSIONS, safe=False)
            logger.info('mAP member [' + mapu['eppn'] + '] is downgrade to contributor membe')

    # nodeをsaveする
    node.save()
    return node


# sync GRDM group to mAP
def mapcore_group_sync_to_map(node):
    '''
    sync group members RDM Project -> mAP Group
    :param node  RDM Node object
    '''

    logger.info('mapcore_group_sync_to_map started for [' + node.title + ']')

    # check Node attribute
    if node.is_deleted:
        logger.info('Node is deleted.  nothing to do.')
        return

    # get the RDM contributor and make lists
    rdm_admin = []
    rdm_members = []
    for member in node.contributors:
        rdmu = RDMmember(node, member)
        rdm_members.append(rdmu)
        if rdmu.is_admin:
            rdm_admin.append(rdmu)
        logger.debug('RDM contributor:\n' + pp(vars(rdmu)))
    rdm_members.sort(key=attrgetter('eppn'))

    # get admin privilaged tokens
    if node.creator:
        priv_user = node.creator
    else:
        if len(rdm_admin) == 0:
            logger.warning('Node (' + node.title + ') has no admin.  cannot sync')
            return
        priv_user = rdm_admin[0]
    mapcore = MAPCore(priv_user)
    logger.info('group [' + node.title + '] sync with [' + priv_user.eppn + ']\'s AccessToken')

    # already combined to mAP group or search by name
    if node.map_group_key is not None:
        logger.info('RDM group [' + node.title + '] is linked to mAP [' + node.map_group_key + '].')
        map_group = mapcore_get_extended_group_info(mapcore, node.map_group_key)
        if map_group is False:
            return
    else:
        # create new group on mAP
        # TODO: RDM may have multiple Project having same name
        #  --> fix get_group_by_name to return multiple groups and select by CGGroup's group_key (may be)
        result = mapcore.get_group_by_name(node.title)  # it returns 1 group only
        if result is not False:
            group_key = result['result']['groups'][0]['group_key']
            map_group = mapcore_get_extended_group_info(mapcore, group_key)
        else:
            # create new mAP group
            result = mapcore.create_group(node.title)
            if result is False:
                logger.error('create_group('' + node.title + '') fail')
                return
            map_group = result['result']['groups'][0]
            group_key = map_group['group_key']
            result = mapcore.edit_group(group_key, node.title, node.description)
            if result is False:
                logger.error('edt_group(' + group_key + ', ' + node.title + ', ' + node.description + ') fail')
                return
            map_group['group_admin_eppn'] = [priv_user.eppn]
            map_group['group_member_list'] = []

        node.map_group_key = map_group['group_name']
        node.save()

    logger.debug('mAP group info:\n' + pp(map_group))
    map_members = map_group['group_member_list']
    map_members.sort(key=lambda u: u['eppn'])

    add, delete, upgrade, downgrade = compare_members(rdm_members, map_members, True)
    #   add: RDMmember,  delete: map_member, upgrade: map_member, downgrade: map_member

    # apply members to mAP group
    for u in add:
        if u.is_admin:
            admin = MAPCore.MODE_ADMIN
        else:
            admin = MAPCore.MODE_MEMBER
        result = mapcore.add_to_group(group_key, u.eppn, admin)
        if result is False:
            return  # error reason is logged by API call
        logger.info('mAP group [' + map_group['group_name'] + '] get new member [' + u.eppn + ']')
    for u in delete:
        result = mapcore.remove_from_group(group_key, u.eppn)
        if result is False:
            return  # error reason is logged by API call
        logger.info('mAP group [' + map_group['group_name'] + ']s member [' + u.eppn + '] is removed')
    for u in upgrade:
        result = mapcore.edit_member(group_key, u.eppn, mapcore.MODE_ADMIN)
        if result is False:
            return  # error reason is logged by API call
        logger.info('mAP group [' + map_group['group_name'] + ']s admin [' + u.eppn + '] is now a member')
    for u in downgrade:
        result = mapcore.edit_member(group_key, u.eppn, mapcore.MODE_MEMBER)
        if result is False:
            return  # error reason is logged by API call
        logger.info('mAP group [' + map_group['group_name'] + ']s member [' + u.eppn + '] is now an admin')

    return

#
# debugging utilities
#


# add a contirbutor to a project
def add_contributor_to_project(node_name, eppn):
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

    ret = node.add_contributor(user, log=True, save=False)
    print('add_contoributor retuns: ' + ret)
    return


if __name__ == '__main__':
    print('In Main')

    if False:  # get mAP group and members -> RDM
        me = OSFUser.objects.get(eppn=sys.argv[1])
        # mapcore_refresh_accesstoken(me)  # token refresh
        # print('name:', me.fullname)
        # print('eppn:', me.eppn)
        #if hasattr(me, 'map_profile'):
        #    print('access_token:', me.map_profile.oauth_access_token)
        #    print('refresh_token:', me.map_profile.oauth_refresh_token)
        group_list = mapcore_users_map_groups(me)
        mapcore_group_sync_to_rdm(group_list[1])

        # for group in group_list:
        #    mapcore_group_sync_to_rdm(group)

    if False:  # get RDM conributors and copy to mAP
        # owner = OSFUser.objects.get(eppn='hnagahara@openidp.nii.ac.jp')
        # mapcore_refresh_accesstoken(owner)  # token refresh
        node = Node.objects.get(title=sys.argv[1])
        mapcore_group_sync_to_map(node)
        pass

    if True:  # test for authcode request
        mapcore_request_authcode(next_url=sys.argv[1])
