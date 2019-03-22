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
#from logging import getLogger
import logging

import hashlib
import requests
import urllib
#from website.app import init_app
#from osf.models.user import OSFUser

# global setting
logger = logging.getLogger(__name__)
logger.setLevel(10)
stdout = logging.StreamHandler()
logger.addHandler(stdout)

map_hostname      = os.getenv('MAPCORE_HOSTNAME', 'https://dev2.cg.gakunin.jp')
map_authcode_path = os.getenv('MAPCORE_AUTHCODE_PATH', '/oauth/shib/shibrequst.php')
map_token_path    = os.getenv('MAPCORE_TOKEN_PATH', '/oauth/token.php')
map_refresh_path  = os.getenv('MAPCORE_REFRESH_PATH', '/oauth/token.php')
map_clientid      = os.getenv('MAPCORE_CLIENTID', 'c6ad1a28a2a6fd61')
map_secret        = os.getenv('MAPCORE_SECRET', 'd31024010c4e00547858fb4eb57cbc8e')
map_redirect      = os.getenv('MAPCORE_REDIRECT', 'https://www.dev1.rdm.nii.ac.jp/oauth_finish')

#
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
#

###
### 下の 2行はテストのための決め打ち項目につき、適宜変更のこと
###
map_api_path        = os.getenv('MAPCORE_API_PATH', '/api2/v1')
map_access_token    = "77bee0c32408b2f3c9b466a6d35747192ae56e54"

class MAPCore:
    MODE_MEMBER = 0     # Ordinary member
    MODE_ADMIN = 2      # Administrator member

    client_secret = False
    access_token = False

    def __init__(self, client_secret, access_token):
        self.client_secret = client_secret
        self.access_token = access_token

    #
    # Get API version.
    #
    def get_api_version(self):
        logger.info("* get_api_version")

        time_stamp, signature = self.calc_signature()

        url = map_hostname + map_api_path + "/version"
        payload = { 'time_stamp': time_stamp, 'signature': signature }
        headers = { "Authorization": "Bearer " + self.access_token }

        r = requests.get(url, headers = headers, params = payload)
        j = self.check_result(r)

        return j

    #
    # Get group information by group name.
    #
    def get_group_by_name(self, group_name):
        logger.info("* get_group_by_name (group_name=" + group_name + ")")

        time_stamp, signature = self.calc_signature()

        url = map_hostname + map_api_path + "/mygroup"
        payload = {
            'time_stamp': time_stamp,
            'signature': signature,
            'searchWord': group_name.encode('utf-8')
        }
        headers = { "Authorization": "Bearer " + self.access_token }

        r = requests.get(url, headers = headers, params = payload)
        j = self.check_result(r)
        if j == False:
            return False

        if len(j["result"]["groups"]) != 1:
            logger.info("  No or multiple group(s) matched")
            return False

        return j

    #
    # Get group information by group key.
    #
    def get_group_by_key(self, group_key):
        logger.info("* get_group_by_key (group_key=" + group_key + ")")

        time_stamp, signature = self.calc_signature()

        url = map_hostname + map_api_path + "/group/" + group_key
        payload = { 'time_stamp': time_stamp, 'signature': signature }
        headers = { "Authorization": "Bearer " + self.access_token }

        r = requests.get(url, headers = headers, params = payload)
        j = self.check_result(r)
        if j == False:
            return False

        if len(j["result"]["groups"]) != 1:
            logger.info("  No or multiple group(s) matched")
            return False

        return j

    #
    # Create new group, and make it public, active and open_member.
    #
    def create_group(self, group_name):
        logger.info("* create_group (group_name=" + group_name + ")")

        #
        # Create new group named "group_name".
        #
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
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(params))
        }

        r = requests.post(url, headers = headers, data = params)
        j = self.check_result(r)
        if (j == False):
            return False
        group_key = j["result"]["groups"][0]["group_key"]
        logger.info("  New geoup has been created (group_key=" + group_key + ")")

        #
        # Change mode of group last created.
        #
        j = self.edit_group(group_key, group_name, "")

        return j

    #
    # Change group properties.
    #
    def edit_group(self, group_key, group_name, introduction):
        logger.info("* edit_group (group_name=" + group_name + ", introduction=" + introduction + ")")

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
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(params))
        }

        r = requests.post(url, headers = headers, data = params)
        j = self.check_result(r)

        return j

    #
    # Get member of group.
    #
    def get_group_members(self, group_key):
        logger.info("* get_group_members (group_key=" + group_key + ")")

        time_stamp, signature = self.calc_signature()

        url = map_hostname + map_api_path + "/member/" + group_key
        payload = { 'time_stamp': time_stamp, 'signature': signature }
        headers = { "Authorization": "Bearer " + self.access_token }

        r = requests.get(url, headers = headers, params = payload)
        j = self.check_result(r)

        return j

    #
    # Get joined group list.
    #
    def get_my_groups(self):
        logger.info("* get_my_groups")

        time_stamp, signature = self.calc_signature()

        url = map_hostname + map_api_path + "/mygroup"
        payload = { 'time_stamp': time_stamp, 'signature': signature }
        headers = { "Authorization": "Bearer " + self.access_token }

        r = requests.get(url, headers = headers, params = payload)
        j = self.check_result(r)

        return j

    #
    # Add to group.
    #
    def add_to_group(self, group_key, eppn, admin):
        logger.info("* add_to_group (group_key=" + group_key + ", eppn=" + eppn + ", admin=" + str(admin) + ")")

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
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json; charset=utf-8",
            "Content-Length": str(len(params))
        }

        r = requests.post(url, headers = headers, data = params)
        j = self.check_result(r)

        return j

    #
    # Remove from group.
    #
    def remove_from_group(self, group_key, eppn):
        logger.info("* remove_from_group (group_key=" + group_key + ", eppn=" + eppn + ")")

        time_stamp, signature = self.calc_signature()

        url = map_hostname + map_api_path + "/member/" + group_key + "/" + eppn
        payload = { 'time_stamp': time_stamp, 'signature': signature }
        headers = { "Authorization": "Bearer " + self.access_token }

        r = requests.delete(url, headers = headers, params = payload)
        j = self.check_result(r)

        return j

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
        s = self.client_secret + self.access_token + time_stamp

        digest = hashlib.sha256(s.encode('utf-8')).hexdigest()
        return time_stamp, digest

    #
    # Check API result status.
    # If any error occurs, a False will be returned.
    #
    def check_result(self, result):
        if result.status_code != requests.codes.ok:
            logger.info("Result status: " + str(result.status_code))
            logger.info("WWW-Authenticate: " + result.headers["WWW-Authenticate"])
            return False

        j = result.json()
        if j["status"]["error_code"] != 0:
            logger.info("Error status: " + str(j["status"]["error_code"]))
            logger.info("Error message: " + j["status"]["error_msg"])
            return False

        return j

#
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#

#
# テスト用メインプログラム
#
mapcore = MAPCore(map_secret, map_access_token)

j = mapcore.get_api_version()
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    logger.info("  version=" + str(j["result"]["version"]))
    logger.info("  revision=" + j["result"]["revision"])
    logger.info("  author=" + j["result"]["author"])

group_name = u"RDM 連携グループ (1)"
introduction = u"RDM 連携のための試験グループ"

#
# 新規グループ作成 (group_name をグループ名として)
#
'''
j = mapcore.create_group(group_name)
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    logger.info(json.dumps(j))
'''

#
# group_name を名前に持つグループを検索
#
j = mapcore.get_group_by_name(group_name)
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    group_key = j["result"]["groups"][0]["group_key"]
    logger.info("  Group key for " + group_name + " found, " + group_key)
    logger.info(json.dumps(j))

#
# group_key で指定したグループの名前、紹介文を変更
#
j = mapcore.edit_group(group_key, group_name, introduction)
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    logger.info(json.dumps(j))

#
# group_key で指定したグループの情報を取得
#
j = mapcore.get_group_by_key(group_key)
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    logger.info(json.dumps(j))

#
# test008@nii.ac.jp を一般会員としてメンバーに追加
#
j = mapcore.add_to_group(group_key, "test008@nii.ac.jp", MAPCore.MODE_MEMBER)
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    logger.info(json.dumps(j))

#
# test008@nii.ac.jp をグループ管理者に変更
#
j = mapcore.edit_member(group_key, "test008@nii.ac.jp", MAPCore.MODE_ADMIN)
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    logger.info(json.dumps(j))

#
# 上記グループのメンバーリストを取得
#
j = mapcore.get_group_members(group_key)
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    for i in range(len(j["result"]["accounts"])):
        logger.info("! " + j["result"]["accounts"][i]["org_name"] + ", eppn=" + j["result"]["accounts"][i]["eppn"] + ", mail=" + j["result"]["accounts"][i]["mail"] + ", admin=" + str(j["result"]["accounts"][i]["admin"]))

#
# test008@nii.ac.jp をメンバーから追加
#
j = mapcore.remove_from_group(group_key, "test008@nii.ac.jp")
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    logger.info(json.dumps(j))

#
# 自身が所属しいているグループのリストを取得
#
j = mapcore.get_my_groups()
if j == False:
    logger.debug("Error")
    sys.exit()
else:
    for i in range(len(j["result"]["groups"])):
        logger.info("! " + j["result"]["groups"][i]["group_name"] + ", key=" + j["result"]["groups"][i]["group_key"])
