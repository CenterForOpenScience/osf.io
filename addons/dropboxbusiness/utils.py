# -*- coding: utf-8 -*-
import os
import logging
import time

import dropbox
from dropbox.dropbox import DropboxTeam
from dropbox.exceptions import ApiError
from dropbox.sharing import MemberSelector, AccessLevel
from dropbox.team import (GroupMembersAddError, GroupMembersRemoveError,
                          GroupSelector, UserSelectorArg, GroupAccessType,
                          MemberAccess)

from osf.models.rdm_addons import RdmAddonOption
from osf.models.external import ExternalAccount
from addons.dropboxbusiness import settings
from admin.rdm_addons.utils import get_rdm_addon_option

logger = logging.getLogger(__name__)

ENABLE_DEBUG = True  # TODO


from pprint import pformat as pf

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error(u'DEBUG_dropboxbusiness: ' + msg)
    else:
        logger.debug(msg)


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


def get_member_profile_list(management_client, group, chunk_size=1000):
    """
    :raises: dropbox.exceptions.DropboxException
    """

    # get first user chunk
    res = management_client.team_groups_members_list(group, chunk_size)
    member_profile_list = [m.profile for m in res.members]

    # get rest of user chunk
    while res.has_more:
        res = management_client.team_groups_members_list_continue(res.cursor)
        member_profile_list += [m.profile for m in res.members]

    return member_profile_list


def get_member_email_list(management_client, group):
    """
    :raises: dropbox.exceptions.DropboxException
    """

    return [p.email for p in get_member_profile_list(management_client, group)]


def sync_members(management_token, group_id, member_email_list):
    """synchronization of members.
    :raises: dropbox.exceptions.DropboxException
    """

    management_client = DropboxTeam(management_token)
    group = GroupSelector.group_id(group_id)

    member_email_set = set(member_email_list)
    db_member_email_set = set(get_member_email_list(management_client, group))

    add_member_list = [
        member_access(email)
        for email in member_email_set - db_member_email_set
    ]
    remove_member_list = [
        member_access(email).user
        for email in db_member_email_set - member_email_set
    ]

    poll_jobs = []

    for memb in add_member_list:
        try:
            poll_jobs.append(
                management_client.team_groups_members_add(group, [memb])
            )
        except ApiError as e:
            if not isinstance(e.error, GroupMembersAddError) or \
               (not e.error.is_users_not_found() and
                    not e.error.is_duplicate_user()):
                raise  # reraise

    for memb in remove_member_list:
        try:
            poll_jobs.append(
                management_client.team_groups_members_remove(group, [memb])
            )
        except ApiError as e:
            if not isinstance(e.error, GroupMembersRemoveError) or \
               not e.error.is_users_not_found():
                raise  # reraise

    for job in poll_jobs:
        poll_team_groups_job(management_client, job)


def get_or_create_admin_group(f_token, m_token, team_info=None):
    group_name = settings.ADMIN_GROUP_NAME
    try_count = 2  # consider race condition
    while try_count > 0:
        if not team_info:
            team_info = TeamInfo(f_token, m_token, admin=False, group=True)
        mclient = team_info.management_client
        group_id = team_info.group_name_to_id.get(group_name)

        if not group_id:
            try:
                group_info = mclient.team_groups_create(group_name)
                group_id = group_info.group_id
            except Exception:
                group_id = None
                team_info = None
                if try_count == 1:
                    raise
        if group_id:
            return group_selector(group_id)
        try_count -= 1
    # not reached
    raise Exception('Unexpected condition')


def create_team_folder(
        fileaccess_token,
        management_token,
        admin_dbmid,
        team_folder_name,
        group_name,
        grdm_member_email_list,
        admin_group
):
    """
    :raises: dropbox.exceptions.DropboxException
    :returns: (team folder id string, group id string)
    """

    fclient = DropboxTeam(fileaccess_token)
    mclient = DropboxTeam(management_token)
    jobs = []

    # create a group for the team members.
    members = [member_access(email) for email in grdm_member_email_list]
    group = group_selector(mclient.team_groups_create(group_name).group_id)
    jobs.append(mclient.team_groups_members_add(group, members))

    for job in jobs:
        poll_team_groups_job(mclient, job)

    team_folder = fclient.team_team_folder_create(team_folder_name)
    fclient.as_admin(admin_dbmid).sharing_add_folder_member(
        team_folder.team_folder_id,
        [file_owner(group.get_group_id()),
         file_owner(admin_group.get_group_id())],
    )
    fclient.as_admin(admin_dbmid).sharing_update_folder_member(
        team_folder.team_folder_id,
        MemberSelector.dropbox_id(group.get_group_id()),
        AccessLevel.editor
    )
    fclient.as_admin(admin_dbmid).sharing_update_folder_member(
        team_folder.team_folder_id,
        MemberSelector.dropbox_id(admin_group.get_group_id()),
        AccessLevel.editor
    )
    return (team_folder.team_folder_id, group.get_group_id())


def get_two_addon_options(institution_id):
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
    # NOTE: management_addon_option.is_allowed is ignored.
    return (fileaccess_addon_option, management_addon_option)


def addon_option_to_token(addon_option):
    if not addon_option:
        return None
    if not addon_option.external_accounts.exists():
        return None
    return addon_option.external_accounts.first().oauth_key


# group_id to group_name
def dict_folder_groups(client, team_folder_id):
    grouo_id_to_name = {}
    cursor = None
    has_more = True
    while has_more:
        if cursor is None:
            lst = client.sharing_list_folder_members(team_folder_id)
        else:
            lst = client.sharing_list_folder_members_continue(cursor)
        cursor = lst.cursor
        if not cursor:
            has_more = False
        for group in lst.groups:
            # group: dropbox.sharing.GroupMembershipInfo
            # group_info: dropbox.sharing.GroupInfo
            #         and dropbox.team_common.GroupSummary
            group_info = group.group
            grouo_id_to_name[group_info.group_id] = group_info.group_name
    return grouo_id_to_name

def update_admin_dbmid(team_id):
    # avoid "ImportError: cannot import name"
    from addons.dropboxbusiness.models import \
        DropboxBusinessManagementProvider
    from addons.dropboxbusiness.models import NodeSettings

    provider_name = DropboxBusinessManagementProvider.short_name
    account = ExternalAccount.objects.get(
        provider=provider_name, provider_id=team_id)
    opt = RdmAddonOption.objects.get(
        provider=provider_name, external_accounts=account)
    info = None
    for addon in NodeSettings.objects.filter(management_option=opt):
        # NodeSettings per a project
        if addon.fileaccess_token is None or \
           addon.management_token is None:
            continue  # skip this project
        try:
            info = TeamInfo(addon.fileaccess_token,
                            addon.management_token,
                            admin=True, groups=True)
            break
        except Exception:
            logger.exception('Unexpected error')
            continue  # skip this project
    if info is None:
        return  # do nothing

    admin_group = get_or_create_admin_group(info.management_client,
                                            info.group_name_to_id,
                                            team_info=info)
    admin_group_id = admin_group.get_group_id()
    sync_members(info.management_token, admin_group_id,
                 info.admin_email_all)

    for addon in NodeSettings.objects.filter(management_option=opt):
        # NodeSettings per a project
        if addon.admin_dbmid not in info.admin_dbmid_all:
            logger.info(u'update dropbox admin_dbmid: {} -> {}'.format(
                addon.admin_dbmid, info.admin_dbmid))
            addon.update_admin_dbmid(info.admin_dbmid)
            addon.cursor = None
            addon.save()

        # check existence of ADMIN_GROUP_NAME group in the team folder members.
        group_id_to_name = dict_folder_groups(info.fileaccess_client_admin,
                                              addon.team_folder_id)
        DEBUG('group_id_to_name=' + pf(group_id_to_name))
        admin_name = group_id_to_name.get(admin_group_id)
        if not admin_name:
            logger.info(u'Admin group for the team folder (GUID={}) is updated. (Because Admin group may be removed from the team folder or settings.ADMIN_GROUP_NAME may be changed.)'.format(addon.owner._id))

            # add admin_group to the team folder
            info.fileaccess_client_admin.sharing_add_folder_member(
                addon.team_folder_id,
                [file_owner(admin_group_id)],
            )
            info.fileaccess_client_admin.sharing_update_folder_member(
                addon.team_folder_id,
                MemberSelector.dropbox_id(admin_group_id),
                AccessLevel.editor
            )


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
    admin_email_all = []
    group_name_to_id = {}
    group_id_to_name = {}
    team_folders = {}  # team_folder_id -> TeamFolder
    team_folder_names = {}  # team_folder name -> TeamFolder
    cursor = None

    def __init__(self, fileaccess_token, management_token,
                 team_info=False, members=False, admin=False, groups=False):
        self.fileaccess_token = fileaccess_token
        self.management_token = management_token
        if team_info:
            self._setup_team_info()
        if admin or members:
            self._setup_members()
        if admin:
            self._setup_admin()  # require members
        if groups:
            self._setup_groups()

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
        self.admin_dbmid_all = []
        self.admin_email_all = []
        for dbmid, role in self.dbmid_to_role.items():
            if role.is_team_admin():
                self.admin_dbmid_all.append(dbmid)
                email = self.dbmid_to_email.get(dbmid)
                if email:
                    self.admin_email_all.append(email)
        DEBUG('admin_dbmid_all: ' + pf(self.admin_dbmid_all))
        DEBUG('admin_email_all: ' + pf(self.admin_email_all))

    def _setup_groups(self):
        self.group_name_to_id = {}
        self.group_id_to_name = {}
        cursor = None
        has_more = True
        client = self.management_client
        while has_more:
            if cursor is None:
                lst = client.team_groups_list()
            else:
                lst = client.team_groups_list_continue()
            has_more = lst.has_more
            cursor = lst.cursor
            for g in lst.groups:
                self.group_name_to_id[g.group_name] = g.group_id
                self.group_id_to_name[g.group_id] = g.group_name
        DEBUG('group_name_to_id: ' + pf(self.group_name_to_id))
        DEBUG('group_id_to_name: ' + pf(self.group_id_to_name))

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
