## mAP core Group / Member syncronization


import os
import sys
import json
import time
import datetime
from logging import getLogger

import urllib
from flask import request

# from website.app import init_app

# global setting
logger = getLogger(__name__)

map_hostname      = os.getenv('MAPCORE_HOSTNAME', 'https://dev2.cg.gakunin.jp')
map_authcode_path = os.getenv('MAPCORE_AUTHCODE_PATH', '/oauth/shib/shibrequst.php')
map_token_path    = os.getenv('MAPCORE_TOKEN_PATH', '/oauth/token.php')
map_refresh_path  = os.getenv('MAPCORE_REFRESH_PATH', '/oauth/token.php')
map_clientid      = os.getenv('MAPCORE_CLIENTID', '52a83b87810af9cb')
map_secret        = os.getenv('MAPCORE_SECRET', '9f734efa99f1c36a5e184547015be41f')
map_redirect      = os.getenv('MAPCORE_REDIRECT', 'https://www.dev1.rdm.nii.ac.jp/oauth_finish')

def mapcore_get_authcode():
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
              "state" : __name__}
    query = url + '?' + urllib.urlencode(params)
    logger.info("redirect to AuthCode request: " + query)
    return query


def mapcore_set_authcode(arg):
    '''decode request parameters'''
    for k, v in arg.items():
        print("RETVAL: %s => %s" % (k, v))
    # logger.info("RETVAL: %s => %s" % (k, v))
    return ('http://www.dev2.rdm.nii.ac.jp/dashboard')


if __name__ == '__main__':
    dic = {"A": 1, "B":2, "C":3}
    mapcore_set_authcode(dic)
    print ("authcode: " + mapcore_get_authcode())

