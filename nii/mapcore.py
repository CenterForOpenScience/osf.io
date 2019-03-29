## mAP core Group / Member syncronization


import os
import sys
import json
import time
from datetime import datetime as dt
import json
from logging import getLogger

import requests
import urllib
from operator import attrgetter

from website.app import init_app
from website import settings
from osf.models.user import OSFUser
from osf.models.node import Node
from osf.models.map import MAPProfile
from nii.api import MAPCore
import framework.auth

# global setting
logger = getLogger(__name__)


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
    params = {"response_type" : "code",
              "redirect_uri" : map_redirect,
              "client_id" : map_clientid,
              "state" : 'GRDM_mAP_AuthCode'}
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
    map_user.save()
    user.map_profile = map_user
    logger.info('User [' + user.eppn + '] get access_token [' + access_token + '] -> saved')
    user.save()


    logger.info('In database:')
    me = OSFUser.objects.get(eppn='nagahara@openidp.nii.ac.jp')
    logger.info('name: ' + me.fullname)
    logger.info('eppn: ' + me.eppn)
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

class RDMmember:
    '''a RDM user'''
    def __init__(self, node, user):
        self.eppn = user.eppn        # ePPN
        self.user_id = user._id      # RDM internal user_id
        if node.has_permission(user, 'admin', check_parent=False):
            self.is_admin = True
            self.access_token = user.map_profile.oauth_access_token
            self.refresh_token = user.map_profile.oauth_refresh_time
        else:
            self.is_admin = False


def mapcore_group_sync(node, is_map2rdm = True):
    '''sync group members RDM Project <--> mAP Group'''
    ''':param node  RDM Node object '''
    ''':param directin boolean True when mAP -> RDM'''

    logger.info("mapcore_group_sync started for [" + node.group.name + ']')

    # check Node attribute
    if node.is_deleted:
        logger.info("Node is deleted.  nothing to do.")
        return

    # get the RDM contributor and make lists
    rdm_members = []
    rdm_admins = []
    for member in node.contributors:
        rdmu = RDMmember(member)
        rdm_members.append(rdmu)
        if rdmu.is_admin:
            rdm_admins.append(rdmu)
    rdm_members.sort(key=attrgetter('eppn'))
    rdm_admins.sort(key=attrgetter('eppn'))

    # get admin privilaged tokens
    if len(rdm_admins) == 0:
        logger.warning('Node (' + node.group.name + ') has no admin.')
        return

    # get the mAP group and make lists
    map_members =[]
    map_admins = []
    logger.info('group [' + node.group.name + '] sync is done by [' + rdm_admins[0].eppn + ']')
    mapcore = MAPCore(map_clientid, map_secret, rdm_admins[0].access_token, rdm_admins[0].refresh_token)
    map_group = mapcore.get_group_by_name(node.group.name)  # 1 returns 1 group only
    if map_group == False:
        return
    map_group = map_group['result']['groups'][0]
    map_member_list = mapcore.get_group_members(map_group['group_key'])
    if map_member_list == False:
        return
    map_member_list = map_member_list['result']['accounts']
    map_member_list.sort(key=lambda u:u['eppn'])
    for map_member in map_member_list:
        if map_member['admin'] == 2:
            map_admins.append(map_member)

    # compare member lists and decide actions





    contributors = node.contributors.objects.all()


    return


if __name__ == '__main__':
    init_app(routes=False, set_backends=False)
    me = OSFUser.objects.get(eppn='nagahra@openidp.nii.ac.jp')
    print('name:', me.fullname)
    print('eppn:', me.eppn)
    print('access_token:', me.oauth_access_token)
    print('refresh_token:', me.oauth_refresh_token)




    #dic = {"A": 1, "B":2, "C":3}
    #mapcore_set_authcode(dic)
    #print ("authcode: " + mapcore_request_authcode())

