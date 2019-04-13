# -*- coding: utf-8 -*-
#
# @COPYRIGHT@
#

import logging
import os
import sys

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
from website import settings

from nii.mapcore_api import MAPCore

map_hostname = settings.MAPCORE_HOSTNAME
map_authcode_path = settings.MAPCORE_AUTHCODE_PATH
map_token_path = settings.MAPCORE_TOKEN_PATH
map_refresh_path = settings.MAPCORE_REFRESH_PATH
map_clientid = settings.MAPCORE_CLIENTID
map_secret = settings.MAPCORE_SECRET
map_redirect = settings.MAPCORE_REDIRECT
map_authcode_magic = settings.MAPCORE_AUTHCODE_MAGIC
my_home = settings.DOMAIN

#
# テスト用メインプログラム
#
if __name__ == '__main__':
    #
    # Get existent OSFUsers.
    #
    for user in OSFUser.objects.all():
        if hasattr(user, 'map_profile'):
            if hasattr(user.map_profile, 'oauth_access_token'):
                print('Refreshing: ' + user.username + ' (' + user.map_profile.oauth_access_token + ')')

                mapcore = MAPCore(user)
                mapcore.refresh_token()

    #
    # 終了
    #
    logger.info('Function completed')
    sys.exit()
