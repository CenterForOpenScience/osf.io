## mAP core Group / Member syncronization


import os
import sys
import json
import time
import datetime
import json
from logging import getLogger

import requests
import urllib

from website.app import init_app
from website import settings
from osf.models.user import OSFUser
from osf.models.map import MAPProfile
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
    logger.info('User [' + user.eppn + '] get access_token [' + access_token)
    user.map_user = MAPProfile.objects.update_or_create(
        oauth_access_token = access_token,
        oauth_refresh_token = refresh_token,
        oauth_refresh_time = datetime.utcnow())
    user.map_user.save()
    user.save()

    return map_hostname  # redirect to home -> will redirect to dashboard


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
    json = res.json()
    logger.info("mapcore_get_accesstoken response: " + json )
    return (json['access_tokes'], json['refresh_token'])


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
    u = user.map_user.objects.get(eppn=user.eppn)
    u.oauth_access_token = json['access_token']
    u.oauth_refresh_token = json['refresh_token']
    u.oauth_refres_time = datetime.utcnow()
    u.save()

    return 0


if __name__ == '__main__':



    #dic = {"A": 1, "B":2, "C":3}
    #mapcore_set_authcode(dic)
    print ("authcode: " + mapcore_request_authcode())

