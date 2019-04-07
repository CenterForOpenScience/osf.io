# -*- coding: utf-8 -*-
#
# @COPYRIGHT@
#

from datetime import datetime as dt
import logging
import os
import sys
import requests
import urllib
import json
from operator import attrgetter
from pprint import pformat as pp

# global setting
logger = logging.getLogger(__name__)
if __name__ == '__main__':
    logger = logging.getLogger('nii.mapcore')
    # stdout = logging.StreamHandler()  # log to stdio
    # logger.addHandler(stdout)
    logger.setLevel(level=logging.DEBUG)
else:
    from osf.models.user import OSFUser, CGGroup
    from osf.models.node import Node
    from osf.models.map import MAPProfile
    from nii.mapcore_api import MAPCore

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

#
# テスト用メインプログラム
#
if __name__ == '__main__':

    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    from website.app import init_app
    init_app(routes=False, set_backends=False)

    from osf.models.user import OSFUser
    from osf.models.node import Node
    from osf.models.map import MAPProfile
    from nii.mapcore_api import MAPCore

    from website import settings

    #
    # Get existent OSFUsers.
    #
    for user in OSFUser.objects.all():
        if hasattr(user, "map_profile"):
            print("Refreshing: " + user.username + " (" + user.map_profile.oauth_access_token + ")")

            mapcore = MAPCore(user)
            mapcore.refresh_token()

    #
    # 終了
    #
    logger.info("Function completed")
    sys.exit()
