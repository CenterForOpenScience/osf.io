# -*- coding: utf-8 -*-
#
# MAPCore class: mAP Core API handling
#
# @COPYRIGHT@
#

import os
import time
import json
import logging
import hashlib
import requests
import urllib

from django.utils import timezone

from website import settings

# TODO import
map_hostname = settings.MAPCORE_HOSTNAME
map_authcode_path = settings.MAPCORE_AUTHCODE_PATH
map_token_path = settings.MAPCORE_TOKEN_PATH
map_refresh_path = settings.MAPCORE_REFRESH_PATH
map_api_path = settings.MAPCORE_API_PATH
map_clientid = settings.MAPCORE_CLIENTID
map_secret = settings.MAPCORE_SECRET
map_authcode_magic = settings.MAPCORE_AUTHCODE_MAGIC

#
# Global settings.
#
VERIFY = True  # for requests.{get,post}(verify=VERIFY)
#VERIFY = False

MAPCORE_DEBUG = True

MAPCORE_API_MEMBER_LIST_BUG_WORKAROUND = True

class MAPCoreLogger(object):
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

logger = logging.getLogger(__name__)
if MAPCORE_DEBUG:
    logger = MAPCoreLogger(logger)


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

    def group_does_not_exist(self):
        if self.mapcore.api_error_code == 208 and \
           self.mapcore.error_message == 'You do not have access permission':
            return True
        return False

    def listing_group_member_is_not_permitted(self):
        if self.mapcore.api_error_code == 206 and \
           self.mapcore.error_message == 'Listing group member is not permitted':
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

    #TODO rdm_mapcore_refresh_token_<user._id>
    #TODO MAPCORE_LOCKDIR
    REFRESH_LOCK = '/var/run/lock/refresh.lck'

    user = False
    client_id = False
    client_secret = False
    http_status_code = None
    api_error_code = None
    error_message = None

    #
    # Constructor.
    #
    def __init__(self, user):
        self.user = user
        self.client_id = settings.MAPCORE_CLIENTID
        self.client_secret = settings.MAPCORE_SECRET

    #
    # Refresh access token.
    #
    def refresh_token(self):
        #logger.debug('MAPCore::refresh_token:')

        self.lock_refresh()

        url = map_hostname + map_refresh_path
        basic_auth = (self.client_id, self.client_secret)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
        }
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': self.user.map_profile.oauth_refresh_token
        }
        params = urllib.urlencode(params)
        logger.debug('  params=' + params)

        r = requests.post(url, auth=basic_auth, headers=headers, data=params, verify=VERIFY)
        if r.status_code != requests.codes.ok:
            logger.info('MAPCore::refresh_token: Refreshing token failed: status_code=' + str(r.status_code) + ', user=' + str(self.user) + ', text=' + r.text)
            self.unlock_refresh()
            return False

        j = r.json()
        if 'error' in j:
            logger.info('MAPCore::refresh_token: Refreshing token failed: ' + j['error'] + ', user=' + str(self.user))
            if 'error_description' in j:
                logger.info('MAPCore::refresh_token: Refreshing token failed: ' + j['error_description'] + ', user=' + str(self.user))
            self.unlock_refresh()
            return False

        logger.info('MAPCore::refresh_token: SUCCESS: user=' + str(self.user))
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

        self.unlock_refresh()

        return True

    #
    # Lock refresh process.
    #
    def lock_refresh(self):

        while True:
            # TODO handle OSError
            fd = os.open(self.REFRESH_LOCK, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0644)
            if fd >= 0:
                os.close(fd)
                return
            time.sleep(1)

    #
    # Unlock refresh process.
    #
    def unlock_refresh(self):

        os.unlink(self.REFRESH_LOCK)

    #
    # Get API version.
    #
    def get_api_version(self):

        logger.debug('MAPCore(user={})::get_api_version:'.format(self.user.username))

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + '/version'
            payload = {'time_stamp': time_stamp, 'signature': signature}
            headers = {'Authorization': 'Bearer ' + self.user.map_profile.oauth_access_token}

            r = requests.get(url, headers=headers, params=payload, verify=VERIFY)
            j = self.check_result(r)
            if j is not False:
                # Function succeeded.
                return j

            if self.is_token_expired(r):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
                count += 1
            else:
                # Any other API error.
                raise self.get_exception()

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Get group information by group name.
    #
    def get_group_by_name(self, group_name):

        logger.debug('MAPCore::get_group_by_name (group_name=' + group_name + ')')

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + '/mygroup'
            payload = {
                'time_stamp': time_stamp,
                'signature': signature,
                'searchWord': group_name.encode('utf-8')
            }
            headers = {'Authorization': 'Bearer ' + self.user.map_profile.oauth_access_token}

            r = requests.get(url, headers=headers, params=payload, verify=VERIFY)
            j = self.check_result(r)
            if j is not False:
                if len(j['result']['groups']) == 0:
                    self.error_message = 'Group not found'
                    logger.debug('  {}'.format(self.error_message))
                    # Group not found.
                    raise self.get_exception()
                # Function succeeded.
                return j

            if self.is_token_expired(r):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
                count += 1
            else:
                # Any other API error.
                raise self.get_exception()

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Get group information by group key.
    #
    def get_group_by_key(self, group_key):

        logger.debug('MAPCore::get_group_by_key (group_key=' + group_key + ')')

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + '/group/' + group_key
            payload = {'time_stamp': time_stamp, 'signature': signature}
            headers = {'Authorization': 'Bearer ' + self.user.map_profile.oauth_access_token}

            r = requests.get(url, headers=headers, params=payload, verify=VERIFY)
            j = self.check_result(r)
            if j is not False:
                if len(j['result']['groups']) == 0:
                    self.error_message = 'Group not found'
                    logger.debug('  {}'.format(self.error_message))
                    # Group not found.
                    raise self.get_exception()
                # Function succeeded.
                return j

            if self.is_token_expired(r):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
                count += 1
            else:
                # Any other API error.
                raise self.get_exception()

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Create new group, and make it public, active and open_member.
    #
    def create_group(self, group_name):

        logger.debug('MAPCore::create_group (group_name=' + group_name + ')')

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        #
        # Create new group named "group_name".
        #
        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            params = {}
            params['request'] = {
                'time_stamp': time_stamp,
                'signature': signature
            }
            params['parameter'] = {
                'group_name': group_name,
                'group_name_en': group_name
            }
            params = json.dumps(params).encode('utf-8')

            url = map_hostname + map_api_path + '/group'
            headers = {
                'Authorization': 'Bearer ' + self.user.map_profile.oauth_access_token,
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': str(len(params))
            }

            r = requests.post(url, headers=headers, data=params, verify=VERIFY)
            j = self.check_result(r)
            if j is not False:
                group_key = j['result']['groups'][0]['group_key']
                logger.debug('  New geoup has been created (group_key=' + group_key + ')')

                #
                # Change mode of group last created.
                #
                j = self.edit_group(group_key, group_name, group_name)
                return j

            if self.is_token_expired(r):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
                count += 1
            else:
                # Any other API error.
                raise self.get_exception()

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Change group properties.
    #
    def edit_group(self, group_key, group_name, introduction):

        logger.debug('MAPCore(user={})::edit_group(group_name={}, introduction={})'.format(self.user.username, group_name, introduction))

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            params = {}
            params['request'] = {
                'time_stamp': time_stamp,
                'signature': signature
            }
            params['parameter'] = {
                'group_name': group_name,
                'group_name_en': '',
                'introduction': introduction,
                'introduction_en': '',
                'public': 1,
                'active': 1,
                'open_member': OPEN_MEMBER_DEFAULT
            }
            params = json.dumps(params).encode('utf-8')

            url = map_hostname + map_api_path + '/group/' + group_key
            headers = {
                'Authorization': 'Bearer ' + self.user.map_profile.oauth_access_token,
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': str(len(params))
            }

            r = requests.post(url, headers=headers, data=params, verify=VERIFY)
            j = self.check_result(r)
            if j is not False:
                # Function succeeded.
                return j

            if self.is_token_expired(r):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
                count += 1
            else:
                # Any other API error.
                raise self.get_exception()

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Get member of group.
    #
    def get_group_members(self, group_key):

        logger.debug('MAPCore::get_group_members (group_key=' + group_key + ')')

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + '/member/' + group_key
            payload = {'time_stamp': time_stamp, 'signature': signature}
            headers = {'Authorization': 'Bearer ' + self.user.map_profile.oauth_access_token}

            r = requests.get(url, headers=headers, params=payload, verify=VERIFY)
            j = self.check_result(r)
            if j is not False:
                # Function succeeded.
                return j

            if self.is_token_expired(r):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
                count += 1
            else:
                # Any other API error.
                raise self.get_exception()

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Get joined group list.
    #
    def get_my_groups(self):

        logger.debug('MAPCore(user={})::get_my_groups:'.format(self.user.username))

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + '/mygroup'
            payload = {'time_stamp': time_stamp, 'signature': signature}
            headers = {'Authorization': 'Bearer ' + self.user.map_profile.oauth_access_token}

            r = requests.get(url, headers=headers, params=payload, verify=VERIFY)
            j = self.check_result(r)
            if j is not False:
                # Function succeeded.
                return j

            if self.is_token_expired(r):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
                count += 1
            else:
                # Any other API error.
                raise self.get_exception()

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Add to group.
    #
    def add_to_group(self, group_key, eppn, admin):

        logger.debug('MAPCore::add_to_group (group_key=' + group_key + ', eppn=' + eppn + ', admin=' + str(admin) + ')')

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            params = {}
            params['request'] = {
                'time_stamp': time_stamp,
                'signature': signature
            }
            params['parameter'] = {
                'admin': admin
            }
            params = json.dumps(params).encode('utf-8')

            url = map_hostname + map_api_path + '/member/' + group_key + '/' + eppn
            headers = {
                'Authorization': 'Bearer ' + self.user.map_profile.oauth_access_token,
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': str(len(params))
            }

            r = requests.post(url, headers=headers, data=params, verify=VERIFY)
            j = self.check_result(r)
            if j is not False:
                # Function succeeded.
                return j

            if self.is_token_expired(r):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
                count += 1
            else:
                # Any other API error.
                raise self.get_exception()

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Remove from group.
    #
    def remove_from_group(self, group_key, eppn):

        logger.debug('MAPCore::remove_from_group (group_key=' + group_key + ', eppn=' + eppn + ')')

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + '/member/' + group_key + '/' + eppn
            payload = {'time_stamp': time_stamp, 'signature': signature}
            headers = {'Authorization': 'Bearer ' + self.user.map_profile.oauth_access_token}

            r = requests.delete(url, headers=headers, params=payload)
            j = self.check_result(r)
            if j is not False:
                # Function succeeded.
                return j

            if self.is_token_expired(r):
                if self.refresh_token() is False:
                    # Automatic refreshing token failed.
                    raise self.get_token_expired()
                count += 1
            else:
                # Any other API error.
                raise self.get_exception()

        # Could not refresh token after retries (may not occur).
        raise self.get_token_expired()

    #
    # Edit member.
    #
    def edit_member(self, group_key, eppn, admin):

        logger.debug('MAPCore::edit_member (group_key=' + group_key + ', eppn=' + eppn + ', admin=' + str(admin) + ')')

        if self.user.map_profile is None:
            # Access token is not issued yet.
            raise self.get_token_expired()

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
        s = self.client_secret + self.user.map_profile.oauth_access_token + time_stamp

        digest = hashlib.sha256(s.encode('utf-8')).hexdigest()
        return time_stamp, digest

    WWW_AUTHENTICATE = 'WWW-Authenticate'
    MSG_ACCESS_TOKEN_EXPIRED = 'Access token expired'
    MSG_INVALID_ACCESS_TOKEN = 'Invalid access token'

    #
    # Check API result status.
    # If any error occurs, a False will be returned.
    #
    def check_result(self, result):
        self.http_status_code = result.status_code
        self.api_error_code = None
        self.error_message = ''

        if result.status_code != requests.codes.ok:
            if self.is_token_expired(result):
                self.error_message = self.MSG_ACCESS_TOKEN_EXPIRED
            else:
                self.error_message = result.headers.get(self.WWW_AUTHENTICATE)
            return False

        j = result.json()
        if j['status']['error_code'] != 0:
            self.api_error_code = j['status']['error_code']
            self.error_message = j['status']['error_msg']
            logger.info('MAPCore(user={})::check_result: error_code={}, error_msg={}'.format(self.user.username, self.api_error_code, self.error_message))
            return False
        return j

    def is_token_expired(self, result):
        if result.status_code != requests.codes.ok:
            s = result.headers.get(self.WWW_AUTHENTICATE)
            if s is None:
                return False
            if s.find(self.MSG_ACCESS_TOKEN_EXPIRED) != -1 \
               or s.find(self.MSG_INVALID_ACCESS_TOKEN) != -1:
                logger.info('MAPCore(user={})::check_result: status_code={}, {}={}'.format(self.user.username, result.status_code, self.WWW_AUTHENTICATE, self.error_message))
                return True
            else:
                return False
        return False
