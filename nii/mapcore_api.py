# -*- coding: utf-8 -*-
#
# MAPCore class: mAP Core API handling
#
# @COPYRIGHT@
#

import sys
import time
import json
import logging
import hashlib
import requests
from urllib.parse import urlencode

from django.utils import timezone
from django.db import transaction

from osf.models.user import OSFUser
from website.settings import (MAPCORE_HOSTNAME,
                              MAPCORE_REFRESH_PATH,
                              MAPCORE_API_PATH,
                              MAPCORE_CLIENTID,
                              MAPCORE_SECRET)

#
# Global settings.
#
VERIFY = True  # for requests.{get,post}(verify=VERIFY)

MAPCORE_API_MEMBER_LIST_BUG_WORKAROUND = False  # 2019/5/24 fixed

MAPCORE_DEBUG = False

# unicode to utf-8
def utf8(s):
    return s.encode('utf-8')

class MAPCoreLogger(object):
    def __init__(self, logger):
        self.logger = logger

    def error(self, msg, *args, **kwargs):
        self.logger.error('MAPCORE: ' + msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning('MAPCORE: ' + msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info('MAPCORE:' + msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug('MAPCORE: ' + msg, *args, **kwargs)

    def setLevel(self, level=logging.INFO):
        self.logger.setLevel(level=level)

class MAPCoreLoggerDebug(object):
    def __init__(self, logger):
        self.logger = logger

    def error(self, msg, *args, **kwargs):
        self.logger.error('MAPCORE_ERROR: ' + msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.error('MAPCORE_WARNING: ' + msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.error('MAPCORE_INFO:' + msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.error('MAPCORE_DEBUG: ' + msg, *args, **kwargs)

    def setLevel(self, level=logging.INFO):
        self.logger.setLevel(level=level)

def mapcore_logger(logger):
    if MAPCORE_DEBUG:
        logger = MAPCoreLoggerDebug(logger)
    else:
        logger = MAPCoreLogger(logger)
    return logger

def mapcore_api_disable_log(level=logging.CRITICAL):
    logger.setLevel(level=level)

logger = mapcore_logger(logging.getLogger(__name__))

class MAPCoreException(Exception):
    def __init__(self, mapcore, ext_message):
        self.mapcore = mapcore
        if ext_message is not None and mapcore is None:
            super(MAPCoreException, self).__init__(
                'ext_message={}'.format(ext_message))
        else:
                super(MAPCoreException, self).__init__(
                    'http_status_code={}, api_error_code={}, message={}, ext_message={}'.format(
                        mapcore.http_status_code, mapcore.api_error_code,
                        mapcore.error_message, ext_message))

    def listing_group_member_is_not_permitted(self):
        if self.mapcore.api_error_code == 206 and \
           self.mapcore.error_message == 'Listing group member is not permitted':
            return True
        return False

    def group_does_not_exist(self):
        if self.mapcore.api_error_code == 208 and \
           self.mapcore.error_message == 'You do not have access permission':
            return True
        return False

class MAPCoreTokenExpired(MAPCoreException):
    def __init__(self, mapcore, ext_message):
        self.caller = mapcore.user
        super(MAPCoreTokenExpired, self).__init__(mapcore, ext_message)

    def __str__(self):
        if self.caller:
            username = self.caller.username
        else:
            username = 'UNKNOWN USER'
        return 'mAP Core Access Token (for {}) is expired'.format(username)


if MAPCORE_API_MEMBER_LIST_BUG_WORKAROUND:
    OPEN_MEMBER_PRIVATE = 1
    OPEN_MEMBER_PUBLIC = 0
    OPEN_MEMBER_MEMBER_ONLY = 2
    OPEN_MEMBER_DEFAULT = OPEN_MEMBER_MEMBER_ONLY
else:
    OPEN_MEMBER_PRIVATE = 0
    OPEN_MEMBER_PUBLIC = 1
    OPEN_MEMBER_MEMBER_ONLY = 2
    OPEN_MEMBER_DEFAULT = OPEN_MEMBER_PUBLIC

def mapcore_group_member_is_private(group_info):
    return group_info['open_member'] == OPEN_MEMBER_PRIVATE

def mapcore_group_member_is_public(group_info):
    return group_info['open_member'] == OPEN_MEMBER_PUBLIC

def mapcore_group_member_is_member_only(group_info):
    return group_info['open_member'] == OPEN_MEMBER_MEMBER_ONLY

class MAPCore(object):
    MODE_MEMBER = 0     # Ordinary member
    MODE_ADMIN = 2      # Administrator member

    user = False
    http_status_code = None
    api_error_code = None
    error_message = None

    #
    # Constructor.
    #
    def __init__(self, user):
        self.user = user

    #
    # Refresh access token.
    #
    def refresh_token0(self):
        #logger.debug('MAPCore::refresh_token:')
        url = MAPCORE_HOSTNAME + MAPCORE_REFRESH_PATH
        basic_auth = (MAPCORE_CLIENTID, MAPCORE_SECRET)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
        }
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': self.user.map_profile.oauth_refresh_token
        }
        params = urlencode(params)
        logger.debug('MAPCore::refresh_token: params=' + params)

        r = requests.post(url, auth=basic_auth, headers=headers, data=params, verify=VERIFY)
        if r.status_code != requests.codes.ok:
            logger.info('MAPCore::refresh_token: Refreshing token failed: status_code=' + str(r.status_code) + ', user=' + str(self.user) + ', text=' + r.text)
            return False

        j = r.json()
        if 'error' in j:
            logger.info('MAPCore::refresh_token: Refreshing token failed: ' + j['error'] + ', user=' + str(self.user))
            if 'error_description' in j:
                logger.info('MAPCore::refresh_token: Refreshing token failed: ' + j['error_description'] + ', user=' + str(self.user))
            return False

        logger.debug('MAPCore::refresh_token: SUCCESS: user=' + str(self.user))
        #logger.debug('  New access_token: ' + j['access_token'])
        #logger.debug('  New refresh_token: ' + j['refresh_token'])

        self.user.map_profile.oauth_access_token = j['access_token']
        self.user.map_profile.oauth_refresh_token = j['refresh_token']

        #
        # Update database.
        #
        self.user.map_profile.oauth_refresh_time = timezone.now()
        self.user.map_profile.save()
        self.user.save()

        return True

    def refresh_token(self):
        try:
            self.lock_refresh()
            return self.refresh_token0()
        finally:
            self.unlock_refresh()

    #
    # Lock refresh process.
    #
    def lock_refresh(self):
        while True:
            #print('before transaction.atomic')
            with transaction.atomic():
                #print('transaction.atomic start')
                u = OSFUser.objects.select_for_update().get(username=self.user.username)
                if not u.mapcore_refresh_locked:
                    #print('before lock')
                    #time.sleep(5) # for debug
                    u.mapcore_refresh_locked = True
                    u.save()
                    logger.debug('OSFUser(' + u.username + ').mapcore_refresh_locked=True')
                    return
            #print('cannot get lock, sleep 1')
            time.sleep(1)

    #
    # Unlock refresh process.
    #
    def unlock_refresh(self):
        with transaction.atomic():
            u = OSFUser.objects.select_for_update().get(username=self.user.username)
            u.mapcore_refresh_locked = False
            u.save()
            logger.debug('OSFUser(' + u.username + ').mapcore_refresh_locked=False')

    #
    # GET|POST|DELETE for methods.
    #
    def req_api(self, method_name, args, requests_method, path, parameters):
        logger.debug('MAPCore(user={}).{}{}'.format(self.user.username, method_name, str(args)))

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        url = MAPCORE_HOSTNAME + MAPCORE_API_PATH + path
        count = 0
        while count < 2:  # retry once
            time_stamp, signature = self.calc_signature()
            if requests_method == requests.get or \
               requests_method == requests.delete:
                payload = {'time_stamp': time_stamp, 'signature': signature}
                if parameters:
                    for k, v in parameters.items():
                        payload[k] = v
                headers = {'Authorization': 'Bearer '
                           + self.user.map_profile.oauth_access_token}
                r = requests_method(url, headers=headers,
                                    params=payload, verify=VERIFY)
            elif requests_method == requests.post:
                params = {}
                params['request'] = {
                    'time_stamp': time_stamp,
                    'signature': signature
                }
                params['parameter'] = parameters
                params = json.dumps(params).encode('utf-8')
                headers = {
                    'Authorization':
                    'Bearer ' + self.user.map_profile.oauth_access_token,
                    'Content-Type': 'application/json; charset=utf-8',
                    'Content-Length': str(len(params))
                }
                r = requests_method(url, headers=headers,
                                    data=params, verify=VERIFY)
            else:
                raise Exception('unknown requests_method')

            j = self.check_result(r, method_name, args)
            if j is not False:
                # Function succeeded.
                return j

            if self.is_token_expired(r, method_name, args):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
            else:
                # Any other API error.
                raise self.get_exception()
            count += 1

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Get API version.
    #
    def get_api_version(self):
        method_name = sys._getframe().f_code.co_name
        return self.req_api(method_name, (), requests.get, '/version', None)

    #
    # Get group information by group name. (unused by mapcore.py)
    #
    def get_group_by_name(self, group_name):
        method_name = sys._getframe().f_code.co_name
        parameters = {'searchWord': group_name.encode('utf-8')}
        path = '/mygroup'
        j = self.req_api(method_name, (group_name,),
                         requests.get, path, parameters)
        if len(j['result']['groups']) == 0:
            self.error_message = 'Group not found'
            logger.debug('  {}'.format(self.error_message))
            # Group not found.
            raise self.get_exception()
        return j

    #
    # Get group information by group key.
    #
    def get_group_by_key(self, group_key):
        method_name = sys._getframe().f_code.co_name
        path = '/group/' + group_key
        j = self.req_api(method_name, (group_key,), requests.get, path, None)
        if len(j['result']['groups']) == 0:
            self.error_message = 'Group not found'
            logger.debug('  {}'.format(self.error_message))
            raise self.get_exception()
        return j

    #
    # delete group by group key.
    #
    def delete_group(self, group_key):
        method_name = sys._getframe().f_code.co_name
        path = '/group/' + group_key
        j = self.req_api(method_name, (group_key,),
                         requests.delete, path, None)
        return j

    #
    # Create new group, and make it public, active and open_member.
    #
    def create_group(self, group_name):
        method_name = sys._getframe().f_code.co_name
        path = '/group'
        parameters = {
            'group_name': group_name,
            'group_name_en': group_name
        }
        j = self.req_api(method_name, (group_name,),
                         requests.post, path, parameters)
        group_key = j['result']['groups'][0]['group_key']
        logger.debug('  New group has been created (group_key=' + group_key + ')')
        # to set description (Empty description is invalid on CG)
        j = self.edit_group(group_key, group_name, group_name)
        return j

    #
    # Change group properties.
    #
    def edit_group(self, group_key, group_name, introduction):
        method_name = sys._getframe().f_code.co_name
        path = '/group/' + group_key
        parameters = {
            'group_name': group_name,
            'group_name_en': '',
            'introduction': introduction,
            'introduction_en': '',
            'public': 1,
            'active': 1,
            'open_member': OPEN_MEMBER_DEFAULT
        }
        j = self.req_api(method_name, (group_key, group_name, introduction),
                         requests.post, path, parameters)
        return j

    #
    # Get member of group.
    #
    def get_group_members(self, group_key):
        method_name = sys._getframe().f_code.co_name
        path = '/member/' + group_key
        parameters = None
        j = self.req_api(method_name, (group_key,),
                         requests.get, path, parameters)
        return j

    #
    # Get joined group list.
    #
    def get_my_groups(self):
        method_name = sys._getframe().f_code.co_name
        path = '/mygroup'
        parameters = None
        j = self.req_api(method_name, (), requests.get, path, parameters)
        return j

    #
    # Add to group.
    #
    def add_to_group(self, group_key, eppn, admin):
        method_name = sys._getframe().f_code.co_name
        path = '/member/' + group_key + '/' + eppn
        parameters = {
            'admin': admin
        }
        j = self.req_api(method_name, (group_key, eppn, admin),
                         requests.post, path, parameters)
        return j

    #
    # Remove from group.
    #
    def remove_from_group(self, group_key, eppn):
        method_name = sys._getframe().f_code.co_name
        path = '/member/' + group_key + '/' + eppn
        parameters = None
        j = self.req_api(method_name, (group_key, eppn),
                         requests.delete, path, parameters)
        return j

    #
    # Edit member.
    #
    def edit_member(self, group_key, eppn, admin):
        #logger.debug('MAPCore::edit_member (group_key=' + group_key + ', eppn=' + eppn + ', admin=' + str(admin) + ')')

        # NOTE: If error occurs, an exception will be thrown.
        j = self.remove_from_group(group_key, eppn)
        j = self.add_to_group(group_key, eppn, admin)

        return j

    #
    # Get MAPCoreException.
    #
    def get_exception(self):
        return MAPCoreException(self, None)

    #
    # Get MAPCoreTokenExpired.
    #
    def get_token_expired(self):
        return MAPCoreTokenExpired(self, None)

    #
    # Calculate API signature.
    #
    def calc_signature(self):

        time_stamp = str(int(time.time()))
        s = MAPCORE_SECRET + self.user.map_profile.oauth_access_token + time_stamp

        digest = hashlib.sha256(s.encode('utf-8')).hexdigest()
        return time_stamp, digest

    WWW_AUTHENTICATE = 'WWW-Authenticate'
    MSG_ACCESS_TOKEN_EXPIRED = 'Access token expired'
    MSG_INVALID_ACCESS_TOKEN = 'Invalid access token'

    #
    # Check API result status.
    # If any error occurs, a False will be returned.
    #
    def check_result(self, result, method_name, args):
        self.http_status_code = result.status_code
        self.api_error_code = None
        self.error_message = ''

        if result.status_code != requests.codes.ok:
            if self.is_token_expired(result, method_name, args):
                self.error_message = self.MSG_ACCESS_TOKEN_EXPIRED
            else:
                self.error_message = result.headers.get(self.WWW_AUTHENTICATE)
                if not self.error_message:
                    self.error_message = result.text
            logger.info('MAPCore(user={},eppn={}).{}{}:check_result: status_code={}, error_msg={}'.format(self.user.username, self.user.eppn, method_name, args, result.status_code, self.error_message))
            return False

        #logger.debug('result.encoding={}'.format(result.encoding))
        j = result.json()
        j = encode_recursive(j)
        if j['status']['error_code'] != 0:
            self.api_error_code = j['status']['error_code']
            self.error_message = j['status']['error_msg']
            logger.info('MAPCore(user={},eppn={}).{}{}:check_result: error_code={}, error_msg={}'.format(self.user.username, self.user.eppn, method_name, args, self.api_error_code, self.error_message))
            return False
        return j

    def is_token_expired(self, result, method_name, args):
        if result.status_code != requests.codes.ok:
            s = result.headers.get(self.WWW_AUTHENTICATE)
            if s is None:
                return False
            #if s.find(self.MSG_ACCESS_TOKEN_EXPIRED) != -1 \
            #   or s.find(self.MSG_INVALID_ACCESS_TOKEN) != -1:
            if result.status_code == 401:  # Unauthorized
                logger.debug('MAPCore(user={},eppn={}).{}{}:is_token_expired: status_code={}, {}={}'.format(self.user.username, self.user.eppn, method_name, args, result.status_code, self.WWW_AUTHENTICATE, self.error_message))
                return True
            else:
                return False
        return False

def encode_recursive(o, encoding='utf-8'):
    if isinstance(o, dict):
        return {encode_recursive(key): encode_recursive(val) for key, val in o.iteritems()}
    elif isinstance(o, list):
        return [encode_recursive(elem) for elem in o]
    elif isinstance(o, str):
        return o.encode(encoding)
    else:
        return o
