# -*- coding: utf-8 -*-
#
# @COPYRIGHT#
#

import os
import sys
import json
import time
import datetime
import json
import re
import logging
import hashlib
import requests
import urllib

from datetime import datetime as dt
from website import settings

#
# Global setting.
#
logger = logging.getLogger(__name__)
logger.setLevel(10)
stdout = logging.StreamHandler()
logger.addHandler(stdout)

map_hostname      = settings.MAPCORE_HOSTNAME
map_authcode_path = settings.MAPCORE_AUTHCODE_PATH
map_token_path    = settings.MAPCORE_TOKEN_PATH
map_refresh_path  = settings.MAPCORE_REFRESH_PATH
map_api_path      = settings.MAPCORE_API_PATH
map_clientid      = settings.MAPCORE_CLIENTID
map_secret        = settings.MAPCORE_SECRET
map_redirect      = settings.MAPCORE_REDIRECT
map_authcode_magic = settings.MAPCORE_AUTHCODE_MAGIC

class MAPCore:
    MODE_MEMBER = 0     # Ordinary member
    MODE_ADMIN = 2      # Administrator member

    user = False
    client_id = False
    client_secret = False

    #
    # Constructor.
    #
    def __init__(self, user):
        self.user = user
        self.client_id = settings.MAPCORE_CLIENTID
        self.client_secret = settings.MAPCORE_SECRET

    #
    # Refresh token.
    #
    def refresh_token(self):
        logger.info("* refresh_token")

        url = map_hostname + map_refresh_path
        logger.info("url=" + url)

        basic_auth = ( self.client_id, self.client_secret )
        logger.info("client_id=" + self.client_id)
        logger.info("client_secret=" + self.client_secret)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
        }
        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.user.map_profile.oauth_refresh_token
        }
        params = urllib.urlencode(params)
        logger.info("refresh_token=" + self.user.map_profile.oauth_refresh_token)
        logger.info("params=" + params)

        r = requests.post(url, auth = basic_auth, headers = headers, data = params)
        if r.status_code != requests.codes.ok:
            logger.info("  Refreshing token failed: " + str(r.status_code))

        logger.info("RESULT=" + r.text)
        #[nii.mapcore_api]  INFO: RESULT=
        #{
        #   "access_token":"2423856290c011307ed69edd69bb243e515e06b3",
        #   "expires_in":3600,
        #   "token_type":"Bearer",
        #   "scope":null,
        #   "refresh_token":"179dfd1c6398bcd9c847d37021e43109f6ae46a0"
        #}
        j = r.json();
        if "error" in j:
            logger.info("  Refreshing token failed: " + j["error"])
            if "error_description" in j:
                logger.info("  Refreshing token failed: " + j["error_description"])
            return False

        self.user.map_profile.oauth_access_token = j["access_token"]
        self.user.map_profile.oauth_refresh_token = j["refresh_token"]

        #
        # Update database.
        #
        self.user.map_profile.oauth_refresh_time = dt.utcnow()
        self.user.map_profile.save()
        self.user.save()

        return True

    #
    # Get API version.
    #
    def get_api_version(self):
        logger.info("* get_api_version")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/version"
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Get group information by group name.
    #
    def get_group_by_name(self, group_name):
        logger.info("* get_group_by_name (group_name=" + group_name + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/mygroup"
            payload = {
                'time_stamp': time_stamp,
                'signature': signature,
                'searchWord': group_name.encode('utf-8')
            }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                if len(j["result"]["groups"]) != 1:
                    logger.info("  No or multiple group(s) matched")
                    return False
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Get group information by group key.
    #
    def get_group_by_key(self, group_key):
        logger.info("* get_group_by_key (group_key=" + group_key + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/group/" + group_key
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                if len(j["result"]["groups"]) != 1:
                    logger.info("  No or multiple group(s) matched")
                    return False
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Create new group, and make it public, active and open_member.
    #
    def create_group(self, group_name):
        logger.info("* create_group (group_name=" + group_name + ")")

        #
        # Create new group named "group_name".
        #
        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            params = { }
            params["request"] = {
                "time_stamp": time_stamp,
                "signature": signature
            }
            params["parameter"] = {
                "group_name": group_name,
                "group_name_en": group_name
            }
            params = json.dumps(params).encode('utf-8')

            url = map_hostname + map_api_path + "/group"
            headers = {
                "Authorization": "Bearer " + self.user.map_profile.oauth_access_token,
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(params))
            }

            r = requests.post(url, headers = headers, data = params)
            j = self.check_result(r)
            if j != False:
                group_key = j["result"]["groups"][0]["group_key"]
                logger.info("  New geoup has been created (group_key=" + group_key + ")")

                #
                # Change mode of group last created.
                #
                j = self.edit_group(group_key, group_name, "")
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Change group properties.
    #
    def edit_group(self, group_key, group_name, introduction):
        logger.info("* edit_group (group_name=" + group_name + ", introduction=" + introduction + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            params = { }
            params["request"] = {
                "time_stamp": time_stamp,
                "signature": signature
            }
            params["parameter"] = {
                "group_name": group_name,
                "group_name_en": group_name,
                "introduction": introduction,
                "introduction_en": introduction,
                "public": 1,
                "active": 1,
                "open_member": 1
            }
            params = json.dumps(params).encode('utf-8')

            url = map_hostname + map_api_path + "/group/" + group_key
            headers = {
                "Authorization": "Bearer " + self.user.map_profile.oauth_access_token,
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(params))
            }

            r = requests.post(url, headers = headers, data = params)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Get member of group.
    #
    def get_group_members(self, group_key):
        logger.info("* get_group_members (group_key=" + group_key + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/member/" + group_key
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Get joined group list.
    #
    def get_my_groups(self):
        logger.info("* get_my_groups")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/mygroup"
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.get(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Add to group.
    #
    def add_to_group(self, group_key, eppn, admin):
        logger.info("* add_to_group (group_key=" + group_key + ", eppn=" + eppn + ", admin=" + str(admin) + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            params = { }
            params["request"] = {
                "time_stamp": time_stamp,
                "signature": signature
            }
            params["parameter"] = {
                "admin": admin
            }
            params = json.dumps(params).encode('utf-8')

            url = map_hostname + map_api_path + "/member/" + group_key + "/" + eppn
            headers = {
                "Authorization": "Bearer " + self.user.map_profile.oauth_access_token,
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": str(len(params))
            }

            r = requests.post(url, headers = headers, data = params)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Remove from group.
    #
    def remove_from_group(self, group_key, eppn):
        logger.info("* remove_from_group (group_key=" + group_key + ", eppn=" + eppn + ")")

        count = 0
        while count < 2:
            time_stamp, signature = self.calc_signature()

            url = map_hostname + map_api_path + "/member/" + group_key + "/" + eppn
            payload = { 'time_stamp': time_stamp, 'signature': signature }
            headers = { "Authorization": "Bearer " + self.user.map_profile.oauth_access_token }

            r = requests.delete(url, headers = headers, params = payload)
            j = self.check_result(r)
            if j != False:
                return j

            if self.is_token_expired(r):
                if self.refresh_token() == False:
                    return False
                count += 1
            else:
                return False

        return False

    #
    # Edit member.
    #
    def edit_member(self, group_key, eppn, admin):
        logger.info("* edit_member (group_key=" + group_key + ", eppn=" + eppn + ", admin=" + str(admin) + ")")

        j = self.remove_from_group(group_key, eppn)
        if j == False:
            return False

        j = self.add_to_group(group_key, eppn, admin)

        return j

    #
    # Calculate API signature.
    #
    def calc_signature(self):
        time_stamp = str(int(time.time()))
        s = self.client_secret + self.user.map_profile.oauth_access_token + time_stamp

        digest = hashlib.sha256(s.encode('utf-8')).hexdigest()
        return time_stamp, digest

    #
    # Check API result status.
    # If any error occurs, a False will be returned.
    #
    def check_result(self, result):
        if result.status_code != requests.codes.ok:
            s = result.headers["WWW-Authenticate"]
            logger.info("Result status: " + str(result.status_code))
            logger.info("WWW-Authenticate: " + s)

            return False

        j = result.json()
        if j["status"]["error_code"] != 0:
            logger.info("Error status: " + str(j["status"]["error_code"]))
            logger.info("Error message: " + j["status"]["error_msg"])
            return False

        return j

    def is_token_expired(self, result):
        if result.status_code != requests.codes.ok:
            s = result.headers["WWW-Authenticate"]
            if s.find("Access token expired") != -1:
                return True
            else:
                return False
        return False
