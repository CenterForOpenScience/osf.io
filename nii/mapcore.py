# -*- coding: utf-8 -*-
## mAP core Group / Member syncronization


from datetime import datetime as dt
import logging
import os
import sys
import requests
import urllib
from operator import attrgetter


# global setting
logger = logging.getLogger(__name__)
if __name__ == '__main__':
    logger.addHandler(logging.StreamHandler())  # log to stdio
else:
    from osf.models.user import OSFUser, CGGroup
    from osf.models.node import Node
    from osf.models.map import MAPProfile
    from nii.mapcore_api import MAPCore

# remove unnesessary s


from website.app import init_app
from website import settings
map_hostname      = settings.MAPCORE_HOSTNAME
map_authcode_path = settings.MAPCORE_AUTHCODE_PATH
map_token_path    = settings.MAPCORE_TOKEN_PATH
map_refresh_path  = settings.MAPCORE_REFRESH_PATH
map_clientid      = settings.MAPCORE_CLIENTID
map_secret        = settings.MAPCORE_SECRET
map_redirect      = settings.MAPCORE_REDIRECT
map_authcode_magic = settings.MAPCORE_AUTHCODE_MAGIC
my_home = settings.DOMAIN


def mapcore_request_authcode():
    '''get an authorization code from mAP. this process will redirect some times.'''
    logger.info("enter mapcore_get_authcode.")
    logger.info("MAPCORE_HOSTNAME: " + map_hostname)
    logger.info("MAPCORE_AUTHCODE_PATH: " + map_authcode_path)
    logger.info("MAPCORE_TOKEN_PATH: " + map_token_path)
    logger.info("MAPCORE_REFRESH_PATH: " + map_refresh_path)
    logger.info("MAPCORE_CLIENTID: " + map_clientid)
    logger.info("MAPCORE_SECRET: " + map_secret)
    logger.info("MAPCORE_REIRECT: " + map_redirect)

    # make call
    url = map_hostname + map_authcode_path
    params = {"response_type": "code",
              "redirect_uri": map_redirect,
              "client_id": map_clientid,
              "state": 'GRDM_mAP_AuthCode'}
    query = url + '?' + urllib.urlencode(params)
    logger.info("redirect to AuthCode request: " + query)
    return query


def mapcore_receive_authcode(user, params):
    '''here is the starting point of user registraion for mAP'''
    ''':param user  OSFUser object of current user'''
    ''':param arg   dict of url parameters in request'''
    if isinstance(user, OSFUser):
        logger.info("in mapcore_receive_authcode, user is instance of OSFUser")
    else:
        logger.info("in mapcore_receive_authcode, user is NOT instance of OSFUser")


    logger.info("get an oatuh response:")
    s = ''
    for k, v in params.items():
        s += "(" + k + ',' + v + ") "
    logger.info("oauth returned parameters: " + s )

    # authorization code check
    if 'code' not in params or 'state' not in params or params['state'] != map_authcode_magic:
        raise ValueError('invalid response from oauth provider')

    # exchange autorization code to access token
    authcode = params['code']
    #authcode = 'AUTHORIZATIONCODESAMPLE'
    #eppn = 'foobar@esample.com'
    (access_token, refresh_token) = mapcore_get_accesstoken(authcode)

    # set mAP attribute into current user
    map_user, created = MAPProfile.objects.get_or_create(eppn = user.eppn)
    if created:
        logger.info("MAPprofile new record created for " + user.eppn)
    map_user.oauth_access_token = access_token
    map_user.oauth_refresh_token = refresh_token
    map_user.oauth_refresh_time = dt.utcnow()
    user.map_profile = map_user
    map_user.save()
    logger.info('User [' + user.eppn + '] get access_token [' + access_token + '] -> saved')
    user.save()

    # DEBUG: read record and print
    logger.info('In database:')
    me = OSFUser.objects.get(eppn=user.eppn)
    logger.info('name: ' + me.fullname)
    logger.info('eppn: ' + me.eppn)
    if hasattr(me, 'map_profile'):
        logger.info('access_token: ' + me.map_profile.oauth_access_token)
        logger.info('refresh_token: ' + me.map_profile.oauth_refresh_token)


    return my_home  # redirect to home -> will redirect to dashboard


def mapcore_get_accesstoken(authcode, clientid = map_clientid, secret = map_secret, rediret = map_redirect):
    '''transfer authorization code to access token and refresh token'''
    '''API call returns the JSON response from mAP authorization code service'''

    logger.info("mapcore_get_accesstoken started.")
    url = map_hostname + map_token_path
    basic_auth = ( map_clientid, map_secret )
    param = {
        "grant_type": "authorization_code",
        "redirect_uri": map_redirect,
        "code": authcode
    }
    param = urllib.urlencode(param)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    }
    res = requests.post(url, data = param, headers = headers, auth = basic_auth)
    res.raise_for_status()  # error check
    logger.info("mapcore_get_accesstoken response: " + res.text )
    json = res.json()
    return (json['access_token'], json['refresh_token'])


def mapcore_refresh_accesstoken(user, force = False):
    '''refresh access token with refresh token'''
    ''':param user     OSFUser'''
    ''':param force    falg to avoid availablity check'''
    ''':return resulut 0..success, 1..must be login again, -1..any error'''

    logger.info('refuresh token for [' + user.eppn + '].')
    url = map_hostname + map_token_path

    # access token availability check
    if not force:
        param = {'access_token' : user.map_user.oauth_access_token}
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
        res = requests.post(url, data=param, headers=headers)
        if res.status_code == 200 and 'success' in res.json():
            return 0  # notihng to do

    # do refresh
    basic_auth = ( map_clientid, map_secret )
    param = {
        "grant_type": "refresh_token",
        "refresh_token": user.map_user.oauth_refresh_token
    }
    param = urllib.urlencode(param)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    }
    res = requests.post(url, data = param, headers = headers, auth = basic_auth)
    json = res.json()
    if res.status_code != 200 or 'access_token' not in json:
        return -1
    logger.info('User [' + user.eppn + '] refresh access_token by [' + json['access_token'])

    # update database
    user.map_profile.oauth_access_token = json['access_token']
    user.map_profile.oauth_refresh_token = json['refreshtoken']
    user.map_profile.oauth_refresh_time = dt.utcnow()
    user.save()

    return 0

###
### sync functions
###

def mapcore_get_users_groups(user):
    '''get nAP groups by a user'''
    ''':param user OSFUser'''
    # get user data from mAP
    return

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
        return self.is_admin == 2 or self.is_admin == 1


# compare member lists and apply  actions
def compare_members(rdm_members, map_members, to_map):
    rdm_index = 0
    map_index = 0
    add = []
    delete = []
    upg = []
    downg = []
    count = max(len(rdm_members), len(map_members))
    while rdm_index < count and map_index < count:
        if map_members[map_index].eppn == rdm_members[rdm_index].eppn:
            # exist in both -> check admin
            if rdm_members[rdm_index].is_admin():
                if map_members[map_index].is_admin():
                    # admin @ both
                    pass
                else:
                    # admin @ rdm only
                    if to_map:
                        upg.append(map_members[map_index])
                    else:
                        downg.append(rdm_members[rdm_index])
            else:
                if map_members[map_index].is_admin():
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

        elif map_members[map_index].eppn < rdm_members[rdm_index].eppn:
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

    return add, delete, upg, downg
    ### to_map:
    ###   add: RDMmember,  delete: map_member, upg: map_member, downg: map_member
    ### not to_map: (to RDM)
    ###   add: map_member, delete: RDMmember,  upg: RDMmember,  downg: RDMmember


def is_node_admin(node, user):
    return node.has_permission(user, 'admin', check_parent=False)


def mapcore_group_sync_to_rdm(map_group):
    '''
    sync group members mAP Group -> RDM Project
    it will scan mAP grous which user belongs, and sync members to to GRDM
    :param map_group : is a dictionary keeps group infomation
    :return:
    '''
    from framework.auth import Auth
    from osf.utils.permissions import CREATOR_PERMISSIONS, DEFAULT_CONTRIBUTOR_PERMISSIONS

    logger.info("mapcore_group_sync_to_rdm started for" + map_group['group_name'])

    # check conditions to sync
    if not map_group['active']:
        logger.info("mAP group [" + map_group['group_name'] + "] is not active  no sync")
        return
    if not map_group['public']:
        logger.info("mAP group [" + map_group['group_name'] + "] is not public  no sync")
        return
    if map_group['open_member'] != 1:  # public only
        logger.info("mAP group [" + map_group['group_name'] + "] member list is not public  no sync")
        return

    # search owner accounts
    owner = None
    for admin_mail in map_group['group_admin']:
        try:
            adminu = OSFUser.objects.get(eppn=admin_mail['mail'])
        except Exception as e:
            logger.info("mAP group admin" + admin_mail['mail'] + "dosn't have account in GRDM.")
            continue
        owner = adminu
    if owner == None:
        logger.warn("all of mAP group [" + map_group['group_name'] + "] admins don't have account in GRDM")
        return
    logger.info("mAP group [" + map_group['group_name'] + "] admin [" + owner.eppn + "] is select to owner")

    # create or get GRDM Project
    node = Node.objects.get_or_create(title=map_group['group_name'], crator=owner, is_public=True, category='project')
    if node.is_deleted:
        logger.info("RDM projet [" + node.title + "] is deleted.  sync aborted.")
        return
    # set mAP group info
    if not hasattr(node, 'group'):
        node.group = CGGroup.objects.get_or_create(group_key=map_group['group_key'])
        node.group.name = map_group['group_name']
        node.group.save()
    node.description = map_group['introduction']

    # take member list from mAP
    mapcore = MAPCore(map_clientid, map_secret, owner.access_token, owner.refresh_token)
    json = mapcore.get_group_members(map_group['group_key'])
    if json == False:
        logger.warn('get_group_members(' + map_group['group_key'] + ') call failed.')
        return
    map_member_list = json['result']['accounts']
    map_member_list.sort(key=lambda u:u['eppn'])
    for mapu in map_member_list:
        if mapu['mail'] in map_group['group_admin']:
            mapu['is_admin'] = True
        else:
            mapu['is_admin'] = False

    # make contirbutor list
    rdm_member_list = []
    if hasattr(node, "contoributor"):
        for rdm_user in node.contoributors.all():
            rdm_member_list.append(RDMmember(node, rdm_user))
    rdm_member_list.sort(key=attrgetter('eppn'))

    # compare
    add, delete, upg, downg = compare_members(rdm_member_list, map_member_list, False)
    ###   add: map_member, delete: RDMmember,  upg: RDMmember,  downg: RDMmember

    # apply members to RDM
    for mapu in add:
        try:
            rdmu = OSFUser.objects.get(eppn=mapu['eppn'])
        except Exception as e:
            logger.info("mAP member [" + mapu['eppn'] + "] is not registed in RDM.  Ignore")
            continue
        if mapu['is_admin']:
            logger.info("mAP member [" + mapu['eppn'] + "] is registed as contributor ADMIN.")
            node.add_contributor(rdmu, log=True, save=False, permissions=CREATOR_PERMISSIONS)
        else:
            logger.info("mAP member [" + mapu['eppn'] + "] is registed as contributor MEMBER.")
            node.add_contributor(rdmu, log=True, save=False)
    for rdmu in delete:
        auth = Auth(user=rdmu)
        node.remove_contributor(rdmu, auth, log=True)
        logger.info("mAP member [" + mapu['eppn'] + "] is remove from contributor")
    for rdmu in upg:
        if not is_node_admin(node, rdmu):
            node.set_permission(rdmu, CREATOR_PERMISSIONS, safe=False)
            logger.info("mAP member [" + mapu['eppn'] + "] is upgrade to admin")
    for rdmu in downg:
        if is_node_admin(node, rdmu):
            node.set_permission(rdmu, DEFAULT_CONTRIBUTOR_PERMISSIONS, safe=False)
            logger.info("mAP member [" + mapu['eppn'] + "] is downgrade to contributor membe")

    # nodeをsaveする
    node.save()


def mapcore_group_sync_to_map(node):
    '''
    sync group members RDM Project -> mAP Group
    :param node  RDM Node object
    '''

    logger.info("mapcore_group_sync_to_map started for [" + node.group.name + ']')

    # check Node attribute
    if node.is_deleted:
        logger.info("Node is deleted.  nothing to do.")
        return

    # get the RDM contributor and make lists
    rdm_owner = None  # FIX IT: it will keep an admin user, not the owner
    rdm_members = []
    for member in node.contributors:
        rdmu = RDMmember(member)
        rdm_members.append(rdmu)
        if not rdm_owner and rdmu.is_admin:
            rdm_owner = rdmu
    rdm_members.sort(key=attrgetter('eppn'))

    # get admin privilaged tokens
    if rdm_owner == None:
        logger.warning('Node (' + node.group.name + ') has no admin.')
        return

    # get the mAP group and make lists
    logger.info('group [' + node.group.name + '] sync is by [' + rdm_owner.eppn + ']')
    mapcore = MAPCore(map_clientid, map_secret, rdm_owner.access_token, rdm_owner.refresh_token)
    map_group = mapcore.get_group_by_name(node.group.name)  # it returns 1 group only
    if map_group == False:
        return
    map_group = map_group['result']['groups'][0]
    map_member_list = mapcore.get_group_members(map_group['group_key'])
    if map_member_list == False:
        return
    map_members = map_member_list['result']['accounts']
    map_members.sort(key=lambda u:u['eppn'])
    group_key = map_group['group_key']

    add, delete, upgrade, downgrade = compare_members(rdm_members, map_members, True)
    ###   add: RDMmember,  delete: map_member, upgrade: map_member, downgrade: map_member

    # apply members to mAP group
    for u in add:
        if u.is_admin():
            admin = MAPCore.MODE_ADMIN
        else:
            admin = MAPCore.MODE_MEMBER
        result = mapcore.add_to_group(group_key, u.eppn, admin)
        if result == False:
            return # error reason is logged by API call
        logger.info("mAP group [" + map_group['group_name'] + "] get new member [" + u.eppn + "]")
    for u in delete:
        result = mapcore.remove_from_group(group_key, u.eppn)
        if result == False:
            return  # error reason is logged by API call
        logger.info("mAP group [" + map_group['group_name'] + "]s member [" + u.eppn + "] is removed")
    for u in upgrade:
        result = mapcore.edit_member(group_key, u.eppn, mapcore.MODE_ADMIN)
        if result == False:
            return # error reason is logged by API call
        logger.info("mAP group [" + map_group['group_name'] + "]s admin [" + u.eppn + "] is now a member")
    for u in downgrade:
        result = mapcore.edit_member(group_key, u.eppn, mapcore.MODE_MEMBER)
        if result == False:
            return # error reason is logged by API call
        logger.info("mAP group [" + map_group['group_name'] + "]s member [" + u.eppn + "] is now an admin")

    return

###
### debugging utilities
###

# print variable type
def startup():
    print("loaded")
    return


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
        print("user is already joind")
        return

    ret = node.add_contributor(user, log=True, save=False)
    print("add_contoributor retuns: " + ret)
    return


if __name__ == '__main__':
    print("In Main")
    ##p = sys.path
    ##del p[0] # remove command path (nii)
    ##sys.path = p
    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    from website.app import init_app
    init_app(routes=False, set_backends=False)

    from osf.models.user import OSFUser
    from osf.models.node import Node
    from osf.models.map import MAPProfile
    from nii.mapcore_api import MAPCore

    from website import settings

    if True:
        me = OSFUser.objects.get(eppn='hnagahara@openidp.nii.ac.jp')
        print('name:', me.fullname)
        print('eppn:', me.eppn)
        if hasattr(me, "map_profile"):
            print('access_token:', me.map_profile.oauth_access_token)
            print('refresh_token:', me.map_profile.oauth_refresh_token)




    #dic = {"A": 1, "B":2, "C":3}
    #mapcore_set_authcode(dic)
    #print ("authcode: " + mapcore_request_authcode())

