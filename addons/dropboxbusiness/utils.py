# -*- coding: utf-8 -*-
import os
import logging
import time

import dropbox
from dropbox.dropbox import DropboxTeam
from dropbox.exceptions import ApiError
from dropbox.sharing import MemberSelector
from dropbox.team import (GroupMembersAddError, GroupMembersRemoveError,
                          GroupSelector, UserSelectorArg, GroupAccessType,
                          MemberAccess)

from osf.models.external import ExternalAccount
from addons.dropboxbusiness import settings
from admin.rdm_addons.utils import get_rdm_addon_option

logger = logging.getLogger(__name__)


def eppn_to_email(eppn):
    return settings.EPPN_TO_EMAIL_MAP.get(eppn, eppn)


def email_to_eppn(email):
    return settings.EMAIL_TO_EPPN_MAP.get(email, email)


def group_selector(group_id):
    return GroupSelector.group_id(group_id)


def member_access(email, role=GroupAccessType.member):
    inner = UserSelectorArg.email(email)
    return MemberAccess(inner, role)


def file_owner(dropbox_id):
    return dropbox.sharing.AddMember(
        MemberSelector.dropbox_id(dropbox_id))


def poll_team_groups_job(management_client, job):
    """
    :raises: dropbox.exceptions.DropboxException
    """

    # [GRDM-15875]
    if job.async_job_id and job.async_job_id.isspace():
        return

    interval = 1
    while True:
        time.sleep(interval)
        st = management_client.team_groups_job_status_get(job.async_job_id)
        if st.is_complete():
            break
        interval *= 2


def get_member_profile_list(manage_client, group, chunk_size=1000):
    """
    :raises: dropbox.exceptions.DropboxException
    """

    # get first user chunk
    res = manage_client.team_groups_members_list(group, chunk_size)
    member_profile_list = [m.profile for m in res.members]

    # get rest of user chunk
    while res.has_more:
        res = manage_client.team_groups_members_list_continue(res.cursor)
        member_profile_list += [m.profile for m in res.members]

    return member_profile_list


def get_member_email_list(manage_client, group):
    """
    :raises: dropbox.exceptions.DropboxException
    """

    return [p.email for p in get_member_profile_list(manage_client, group)]


def sync_members(management_access_token, group_id, grdm_member_email_list):
    """synchronization of members.
    :raises: dropbox.exceptions.DropboxException
    """

    manage_client = DropboxTeam(management_access_token)
    group = GroupSelector.group_id(group_id)

    grdm_member_email_set = set(grdm_member_email_list)
    db_member_email_set = set(get_member_email_list(manage_client, group))

    add_member_list = [
        member_access(email)
        for email in grdm_member_email_set - db_member_email_set
    ]
    remove_member_list = [
        member_access(email).user
        for email in db_member_email_set - grdm_member_email_set
    ]

    poll_jobs = []

    for memb in add_member_list:
        try:
            poll_jobs.append(
                manage_client.team_groups_members_add(group, [memb])
            )
        except ApiError as e:
            if not isinstance(e.error, GroupMembersAddError) or \
               not e.error.is_users_not_found():
                raise  # reraise

    for memb in remove_member_list:
        try:
            poll_jobs.append(
                manage_client.team_groups_members_remove(group, [memb])
            )
        except ApiError as e:
            if not isinstance(e.error, GroupMembersRemoveError) or \
               not e.error.is_users_not_found():
                raise  # reraise

    for job in poll_jobs:
        poll_team_groups_job(manage_client, job)


def create_team_folder(
        fileaccess_token,
        management_token,
        admin_dbmid,
        team_folder_name,
        group_name,
        grdm_member_email_list
):
    """
    :raises: dropbox.exceptions.DropboxException
    :returns: (team folder id string, group id string)
    """

    fclient = DropboxTeam(fileaccess_token)
    mclient = DropboxTeam(management_token)

    members = [member_access(email) for email in grdm_member_email_list]

    team_folder = fclient.team_team_folder_create(team_folder_name)
    group = group_selector(mclient.team_groups_create(group_name).group_id)
    job = mclient.team_groups_members_add(group, members)
    poll_team_groups_job(mclient, job)
    fclient.as_admin(admin_dbmid).sharing_add_folder_member(
        team_folder.team_folder_id,
        [file_owner(group.get_group_id())]
    )

    return (team_folder.team_folder_id, group.get_group_id())


def get_two_external_accounts(institution_id):
    # avoid "ImportError: cannot import name"
    from addons.dropboxbusiness.models import \
        (DropboxBusinessFileaccessProvider,
         DropboxBusinessManagementProvider)
    fileaccess_addon_option = get_rdm_addon_option(
        institution_id, DropboxBusinessFileaccessProvider.short_name,
        create=False)
    management_addon_option = get_rdm_addon_option(
        institution_id, DropboxBusinessManagementProvider.short_name,
        create=False)
    if fileaccess_addon_option is None or \
       management_addon_option is None:
        return None
    if not fileaccess_addon_option.is_allowed:
        return None
    # NOTE: management_addon_option.is_allowed is not used.
    try:
        f_account = fileaccess_addon_option.external_accounts.first()
        m_account = management_addon_option.external_accounts.first()
    except Exception:
        return None
    if f_account.provider_id == m_account.provider_id:  # same team_id
        return (f_account, m_account)
    return None


def update_admin_dbmid(team_id):
    for account in ExternalAccount.objects.filter(provider_id=team_id):
        for addon in account.dropboxbusiness_management_node_settings.all():
            # NodeSetting
            if addon.fileaccess_account is None or \
               addon.management_account is None:
                continue  # skip
            info = TeamInfo(addon.fileaccess_account, addon.management_account)
            if addon.admin_dbmid not in info.admin_dbmid_all:
                logger.info(u'update admin_dbmid: {} -> {}'.format(
                    addon.admin_dbmid, info.admin_dbmid))
                addon.update_admin_dbmid(info.admin_dbmid)
                addon.cursor = None
                addon.save()


from pprint import pformat as pf  # TODO unnecessary
def DEBUG(msg):  # TODO unnecessary
    logger.error(u'DEBUG: ' + msg)

class TeamFolder(object):
    team_folder_id = None
    cursor = None
    metadata = None

    def __init__(self, metadata):
        self.team_folder_id = metadata.team_folder_id
        self.update_metadata(metadata)

    def __repr__(self):
        return u'name={}'.format(self.metadata.name)

    def update_metadata(self, metadata):
        self.metadata = metadata

class TeamInfo(object):
    team_id = None
    name = None
    fileaccess_token = None
    management_token = None
    _fileaccess_client = None
    _management_client = None
    dbid_to_email = {}
    dbid_to_role = {}
    dbid_to_account_id = {}
    email_to_dbmid = {}
    admin_dbmid_all = []
    team_folders = {}  # team_folder_id -> TeamFolder
    team_folder_names = {}  # team_folder name -> TeamFolder
    cursor = None

    def __init__(self, fileaccess_account, management_account):
        self.fileaccess_token = fileaccess_account.oauth_key
        self.management_token = management_account.oauth_key
        #self._setup_team_info()  #TODO necessary?
        self._setup_members()
        self._setup_admin()

    @property
    def admin_dbmid(self):
        return self.admin_dbmid_all[0]  # select one admin user

    @property
    def management_client(self):
        if self._management_client is None:
            self._management_client = DropboxTeam(self.management_token)
        return self._management_client

    def _fileaccess_client_check(self):
        if self._fileaccess_client is None:
            self._fileaccess_client = DropboxTeam(self.fileaccess_token)

    @property
    def fileaccess_client_team(self):
        self._fileaccess_client_check()
        return self._fileaccess_client

    @property
    def fileaccess_client_admin(self):
        self._fileaccess_client_check()
        DEBUG('Admin: email={}'.format(self.dbmid_to_email[self.admin_dbmid]))
        return self._fileaccess_client.as_admin(self.admin_dbmid)

    ### not property
    def fileaccess_client_with_path_root(self, namespace_id):
        self._fileaccess_client_check()
        pr = dropbox.common.PathRoot.namespace_id(namespace_id)
        return self._fileaccess_client.with_path_root(pr).as_admin(self.admin_dbmid)

    ### not property
    def fileaccess_client_user(self, member_id):
        self._fileaccess_client_check()
        return self._fileaccess_client.as_user(member_id)

    def _setup_team_info(self):
        i = self.management_client.team_get_info()
        self.team_id = i.team_id
        self.name = i.name
        DEBUG(u'team info(manage): {}: {}'.format(self.team_id, self.name))

    def _setup_members(self):
        cursor = None
        has_more = True
        self.dbmid_to_email = {}  # member_id
        self.dbmid_to_role = {}
        self.dbmid_to_account_id = {}
        self.email_to_dbmid = {}
        # NOTE: client = self.management_client ... usable
        client = self.fileaccess_client_team
        while has_more:
            if cursor is None:
                ms = client.team_members_list()
            else:
                ms = client.team_members_list_continue(cursor)
            has_more = ms.has_more
            cursor = ms.cursor
            for m in ms.members:
                p = m.profile
                self.dbmid_to_email[p.team_member_id] = p.email
                self.dbmid_to_role[p.team_member_id] = m.role
                self.dbmid_to_account_id[p.team_member_id] = p.account_id
        DEBUG('dbmid_to_email: ' + pf(self.dbmid_to_email))
        DEBUG('dbmid_to_role: ' + pf(self.dbmid_to_role))
        DEBUG('dbmid_to_account_id: ' + pf(self.dbmid_to_account_id))
        self.email_to_dbmid = {v: k for k, v in self.dbmid_to_email.items()}
        DEBUG('email_to_dbmid: ' + pf(self.email_to_dbmid))

    def _setup_admin(self):
        self.admin_list = []
        for k, role in self.dbmid_to_role.items():
            if role.is_team_admin():
                self.admin_list.append(k)
        DEBUG('admin_list: ' + pf(self.admin_list))

    def _update_team_folders(self):
        cursor = None
        has_more = True
        # NOTE: client = self.management_client
        #       -> ERROR: Your API app is not allowed to call this function.
        client = self.fileaccess_client_team
        while has_more:
            if cursor is None:
                fs = client.team_team_folder_list()
            else:
                fs = client.team_team_folder_list_continue()
            has_more = fs.has_more
            cursor = fs.cursor
            for meta in fs.team_folders:
                i = meta.team_folder_id
                team_folder = self.team_folders.get(i)
                if team_folder:
                    team_folder.update_metadata(meta)
                else:  # new team folder
                    tf = TeamFolder(meta)
                    self.team_folders[i] = tf
                    self.team_folder_names[meta.name] = tf

    # return (team_folder_id, team_folder_name, subpath)
    def team_folder_path(self, path_display):
        p = path_display
        team_folder_name = None
        while True:
            head, tail = os.path.split(p)
            if head == '/':
                team_folder_name = tail
                break
            p = head
        if team_folder_name is None:
            return None
        tf = self.team_folder_names.get(team_folder_name)
        if tf is None:
            return None
        subpath = path_display[len(u'/' + team_folder_name):]
        return (tf.team_folder_id, team_folder_name, subpath)
