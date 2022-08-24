# -*- coding: utf-8 -*-
import os
import logging
import time
import collections
import threading
from pprint import pformat as pf
import base64
import math

import dropbox
from dropbox.dropbox import Dropbox, DropboxTeam
from dropbox.exceptions import ApiError
from dropbox.sharing import MemberSelector, AccessLevel
from dropbox.team import (GroupMembersAddError, GroupMembersRemoveError,
                          GroupSelector, UserSelectorArg, GroupAccessType,
                          MemberAccess)

from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from celery.contrib.abortable import AbortableTask

from osf.models import BaseFileNode, OSFUser
from osf.models.external import ExternalAccount
# from osf.models.nodelog import NodeLog
from osf.models.rdm_addons import RdmAddonOption
from addons.dropboxbusiness import settings, lock
from admin.rdm_addons.utils import get_rdm_addon_option
from website.util import timestamp, waterbutler
from api.base import settings as api_settings
from framework.auth import Auth
from framework.celery_tasks import app as celery_app

logger = logging.getLogger(__name__)

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error(u'DEBUG_dropboxbusiness: ' + msg)
    else:
        logger.debug(msg)

if not ENABLE_DEBUG:
    logging.getLogger('dropbox').setLevel(logging.CRITICAL)

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


def get_member_dbmid_list(management_client, group):
    """
    :raises: dropbox.exceptions.DropboxException
    """

    return [p.team_member_id for p in get_member_profile_list(management_client, group)]


def sync_members(management_token, group_id, member_email_list):
    """synchronization of members.
    :raises: dropbox.exceptions.DropboxException
    """

    management_client = DropboxTeam(management_token)
    group = group_selector(group_id)

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

        created = False
        if not group_id:
            try:
                group_info = mclient.team_groups_create(group_name)
                group_id = group_info.group_id
                created = True
            except Exception:
                group_id = None
                team_info = None
                if try_count == 1:
                    raise
        if group_id:
            return group_selector(group_id), created
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
        admin_group,
        team_name
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

    def delete_unused_group():
        try:
            mclient.team_groups_delete(group)
        except Exception:
            logger.exception('The team group({}@{}) cannot be deleted.'.format(group_name, team_name))
            # ignored

    try:
        job = mclient.team_groups_members_add(group, members)
        jobs.append(job)
    except Exception:
        delete_unused_group()
        raise
    for job in jobs:
        poll_team_groups_job(mclient, job)

    try:
        team_folder = fclient.team_team_folder_create(team_folder_name)
    except Exception:
        delete_unused_group()
        raise

    def delete_unused_team_folder():
        try:
            fclient.team_team_folder_archive(
                team_folder.team_folder_id, force_async_off=True)
            fclient.team_team_folder_permanently_delete(
                team_folder.team_folder_id)
        except Exception:
            logger.exception('The team Folder({}@{}) cannot be deleted.'.format(team_folder_name, team_name))
            # ignored

    try:
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
    except Exception:
        delete_unused_team_folder()
        delete_unused_group()
        raise
    return (team_folder.team_folder_id, group.get_group_id())


def get_two_addon_options(institution_id, allowed_check=True):
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
    if allowed_check and not fileaccess_addon_option.is_allowed:
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


def get_current_admin_group_and_sync(team_info):
    admin_group, created = get_or_create_admin_group(
        team_info.management_client,
        team_info.group_name_to_id,
        team_info=team_info)
    admin_group_id = admin_group.get_group_id()
    should_update = False
    admin_dbmid_list = []
    if created:
        should_update = True
    else:
        # to update admin_dbmid based on the admin group (GRDM-ADMIN)
        admin_dbmid_list = get_member_dbmid_list(team_info.management_client,
                                                 admin_group)
        if len(admin_dbmid_list) == 0:
            should_update = True
        elif len(set(admin_dbmid_list) - set(team_info.admin_dbmid_all)) > 0:
            # Non-admin users exist in the GRDM-ADMIN group
            should_update = True
    if should_update:
        sync_members(team_info.management_token, admin_group_id,
                     team_info.admin_email_all)
        admin_dbmid_list = team_info.admin_dbmid_all
    return admin_group, admin_dbmid_list


def get_current_admin_dbmid(m_option, admin_dbmid_list):
    from addons.dropboxbusiness.models import NodeSettings

    dbmid_list = []
    for addon in NodeSettings.objects.filter(management_option=m_option):
        if addon.owner.is_deleted:
            continue
        dbmid_list.append(addon.admin_dbmid)
    if len(dbmid_list) == 0:
        return admin_dbmid_list[0]
    c = collections.Counter(dbmid_list)
    # select majority
    most = c.most_common()
    current_admin_dbmid = most[0][0]
    if current_admin_dbmid not in admin_dbmid_list:
        current_admin_dbmid = admin_dbmid_list[0]
    return current_admin_dbmid


def update_admin_dbmid(team_id):
    # avoid "ImportError: cannot import name"
    from addons.dropboxbusiness.models import \
        (DropboxBusinessFileaccessProvider,
         DropboxBusinessManagementProvider)
    from addons.dropboxbusiness.models import NodeSettings

    f_provider_name = DropboxBusinessFileaccessProvider.short_name
    m_provider_name = DropboxBusinessManagementProvider.short_name

    f_account = ExternalAccount.objects.filter(
        provider=f_provider_name, provider_id=team_id).first()
    m_account = ExternalAccount.objects.filter(
        provider=m_provider_name, provider_id=team_id).first()
    if f_account is None or m_account is None:
        return

    f_token = f_account.oauth_key
    m_token = m_account.oauth_key
    if f_token is None or m_token is None:
        return

    m_opt = RdmAddonOption.objects.filter(
        provider=m_provider_name, external_accounts=m_account).first()
    if m_opt is None:
        return

    MAX_THREAD_NUM = 10
    team_info = TeamInfo(f_token, m_token,
                         max_connections=MAX_THREAD_NUM,
                         team_info=True, admin=True, groups=True)
    admin_group, admin_dbmid_list = get_current_admin_group_and_sync(team_info)
    new_admin_dbmid = get_current_admin_dbmid(m_opt, admin_dbmid_list)
    # update admin_dbmid for fileaccess_client_admin
    team_info.set_admin_dbmid(new_admin_dbmid)

    # update "Authorized by ..."
    admin_email = team_info.dbmid_to_email.get(new_admin_dbmid)
    if admin_email:
        dispname = u'{} ({})'.format(admin_email, team_info.name)
        f_account.display_name = dispname
        f_account.save()
        m_account.display_name = dispname
        m_account.save()

    # update admin_dbmid for all NodeSettings
    log_once = True
    for addon in NodeSettings.objects.filter(management_option=m_opt):
        if addon.owner.is_deleted:
            continue

        # NodeSettings per a project
        if addon.admin_dbmid != new_admin_dbmid:
            if log_once:
                logger.info(u'update dropbox admin_dbmid (team={}): {} -> {}'.format(
                    team_info.name, addon.admin_dbmid, new_admin_dbmid))
                log_once = False
            addon.set_admin_dbmid(new_admin_dbmid)
            addon.list_cursor = None
            addon.save()

    admin_group_id = admin_group.get_group_id()

    def check_admin_group(addon):
        # check existence of ADMIN_GROUP_NAME group
        # in the team folder members.
        group_id_to_name = dict_folder_groups(
            team_info.fileaccess_client_admin,
            addon.team_folder_id)
        DEBUG('group_id_to_name=' + pf(group_id_to_name))
        admin_name = group_id_to_name.get(admin_group_id)
        if not admin_name:
            logger.info(u'Admin group for the team folder (node={}) is updated. (Because Admin group may be removed from the team folder or settings.ADMIN_GROUP_NAME may be changed.)'.format(addon.owner._id))
            # add admin_group to the team folder
            team_info.fileaccess_client_admin.sharing_add_folder_member(
                addon.team_folder_id,
                [file_owner(admin_group_id)],
            )
            team_info.fileaccess_client_admin.sharing_update_folder_member(
                addon.team_folder_id,
                MemberSelector.dropbox_id(admin_group_id),
                AccessLevel.editor
            )

    threads = []
    for addon in NodeSettings.objects.filter(management_option=m_opt):
        if addon.owner.is_deleted:
            continue

        if len(threads) >= MAX_THREAD_NUM:
            th = threads.pop(0)
            th.join()
        th = threading.Thread(target=check_admin_group, args=(addon,))
        th.start()
        threads.append(th)

    for th in threads:
        th.join()

def rename_group(mclient, group_id, new_group_name):
    mclient.team_groups_update(group_selector(group_id),
                               return_members=False,
                               new_group_name=new_group_name)

def create_folder(team_info, team_folder_id, path):
    client = team_info.fileaccess_client_admin_with_path_root(team_folder_id)
    try:
        client.files_create_folder(path)
        DEBUG(u'create folder: {}'.format(path))
        return True
    except ApiError:
        logger.exception(u'cannot create a folder: {}'.format(path))
        return False

def are_same_team(addon1, addon2):
    return addon1.fileaccess_option == addon2.fileaccess_option

def copy_folders(team_info, src_addon, src_path, dest_addon, dest_path):
    if not are_same_team(src_addon, dest_addon):
        return

    src_team_folder_id = src_addon.team_folder_id
    dest_team_folder_id = dest_addon.team_folder_id

    client = team_info.fileaccess_client_admin_with_path_root(
        src_team_folder_id)
    if src_path == '/':
        src_path = ''  # '/' is not supported by files_list_folder()
    cursor = None
    has_more = True
    folders = []
    while has_more:
        if not cursor:
            lst = client.files_list_folder(src_path, recursive=False)
        else:
            lst = client.files_list_folder_continue(cursor)
        has_more = lst.has_more
        cursor = lst.cursor  # save
        for ent in lst.entries:
            if isinstance(ent, dropbox.files.FolderMetadata):
                folders.append(ent.path_display)

    for child_src_folder in folders:
        folder_name = os.path.basename(child_src_folder.rstrip('/'))
        child_dest_folder = os.path.join(dest_path, folder_name)
        DEBUG(u'child_src_folder={}, child_dest_folder={}'.format(child_src_folder, child_dest_folder))
        res = create_folder(team_info, dest_team_folder_id, child_dest_folder)
        if res:
            copy_folders(team_info,
                         src_addon, child_src_folder,
                         dest_addon, child_dest_folder)
        else:
            dest_node = dest_addon.owner
            dest_provider = dest_addon.short_name
            logger.error(u'cannot create new folder: node guid={}, provider={}, path={}'.format(dest_node._id, dest_provider, child_dest_folder))

# return (timestamp_data, timestamp_status, context)
def get_timestamp(node_settings, path):
    team_info = TeamInfo(node_settings.fileaccess_token,
                         node_settings.management_token,
                         timestamp=True,
                         admin_dbmid=node_settings.admin_dbmid)
    return team_info.get_timestamp(node_settings.team_folder_id, path)

def set_timestamp(node_settings, path, timestamp_data, timestamp_status, team_info=None):
    if team_info is None:
        team_info = TeamInfo(node_settings.fileaccess_token,
                             node_settings.management_token,
                             timestamp=True,
                             admin_dbmid=node_settings.admin_dbmid)
    team_info.set_timestamp(node_settings.team_folder_id, path,
                            timestamp_data, timestamp_status)


class TeamFolder(object):
    team_folder_id = None
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
    _fileaccess_client2 = None  # for bugfix
    _management_client = None
    dbmid_to_email = {}
    dbmid_to_role = {}
    dbmid_to_dbid = {}
    email_to_dbmid = {}
    dbid_to_dbmid = {}
    _admin_dbmid = None
    admin_dbmid_all = []
    admin_email_all = []
    group_name_to_id = {}
    group_id_to_name = {}
    team_folders = {}  # team_folder_id -> TeamFolder
    team_folder_names = {}  # team_folder name -> TeamFolder
    property_fields = set()
    property_template_id = None

    def __init__(self, fileaccess_token, management_token,
                 max_connections=8,
                 connecttest=False,
                 team_info=False, members=False,
                 admin=False, admin_dbmid=None,
                 groups=False,
                 file_properties=False, timestamp=False):
        DEBUG('init TeamInfo()')
        self.fileaccess_token = fileaccess_token
        self.management_token = management_token
        self.session = dropbox.dropbox.create_session(
            max_connections=max_connections)

        if timestamp:
            if admin_dbmid is None:
                admin = True
            file_properties = True
        if admin:
            members = True

        if connecttest:
            members = True
            self._update_team_folders()

        if team_info:
            self._setup_team_info()
        if members:
            self._setup_members()
        if admin:
            self._setup_admin()  # require members
        if groups:
            self._setup_groups()
        if file_properties:
            self._setup_file_properties()

        if admin_dbmid:
            self.set_admin_dbmid(admin_dbmid)

    @property
    def admin_dbmid(self):
        if not self._admin_dbmid:
            # select one admin user
            self._admin_dbmid = self.admin_dbmid_all[0]
        return self._admin_dbmid

    def set_admin_dbmid(self, admin_dbmid):
        self._admin_dbmid = admin_dbmid

    @property
    def management_client(self):
        if self._management_client is None:
            self._management_client = DropboxTeam(
                self.management_token, session=self.session)
        return self._management_client

    def _fileaccess_client_check(self):
        if self._fileaccess_client is None:
            self._fileaccess_client = DropboxTeam(
                self.fileaccess_token, session=self.session)

    @property
    def fileaccess_client_team(self):
        self._fileaccess_client_check()
        return self._fileaccess_client

    def _fileaccess_client2_check(self):
        if self._fileaccess_client2 is None:
            self._fileaccess_client2 = Dropbox(
                self.fileaccess_token, session=self.session)

    @property
    def fileaccess_client_team2(self):
        self._fileaccess_client2_check()
        return self._fileaccess_client2

    @property
    def fileaccess_client_admin(self):
        self._fileaccess_client_check()
        DEBUG('Admin: email={}'.format(self.dbmid_to_email[self.admin_dbmid]))
        return self._fileaccess_client.as_admin(self.admin_dbmid)

    ### not property
    def fileaccess_client_admin_with_path_root(self, namespace_id):
        self._fileaccess_client_check()
        pr = dropbox.common.PathRoot.namespace_id(namespace_id)
        return self._fileaccess_client.with_path_root(pr).as_admin(self.admin_dbmid)

    ### not property
    def fileaccess_client_user(self, member_id):
        self._fileaccess_client_check()
        return self._fileaccess_client.as_user(member_id)

    ### not property
    def fileaccess_client_user_with_path_root(self, dbmid, namespace_id):
        self._fileaccess_client_check()
        pr = dropbox.common.PathRoot.namespace_id(namespace_id)
        return self._fileaccess_client.with_path_root(pr).as_user(dbmid)

    def _setup_team_info(self):
        i = self.management_client.team_get_info()
        self.team_id = i.team_id
        self.name = i.name
        DEBUG(u'team info(manage): {}: {}'.format(self.team_id, self.name))

    def _setup_members(self):
        cursor = None
        has_more = True
        # dbmid: team member_id
        # dbid : account_id
        self.dbmid_to_email = {}
        self.dbmid_to_role = {}
        self.dbmid_to_dbid = {}
        self.email_to_dbmid = {}
        self.dbid_to_email = {}
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
                self.dbmid_to_dbid[p.team_member_id] = p.account_id
                self.email_to_dbmid[p.email] = p.team_member_id
                self.dbid_to_email[p.account_id] = p.email

        DEBUG('dbmid_to_email: ' + pf(self.dbmid_to_email))
        DEBUG('dbmid_to_role: ' + pf(self.dbmid_to_role))
        DEBUG('dbmid_to_dbid: ' + pf(self.dbmid_to_dbid))
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
        # NOTE: using "client = self.management_client"
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

    def list_updated_files(self, cursor):
        self._update_team_folders()
        client = self.fileaccess_client_user(self.admin_dbmid)
        has_more = True
        files = []
        while has_more:
            if not cursor:
                lst = client.files_list_folder('', recursive=True)
            else:
                lst = client.files_list_folder_continue(cursor)
            has_more = lst.has_more
            cursor = lst.cursor  # save
            for ent in lst.entries:
                files.append(FileAttr(self, ent))
        return files, cursor

    def _prop_split_key(self, name, s):
        return '{}-{}'.format(name, s)

    def _prop_split_data_num_key(self, name):
        return self._prop_split_key(name, 'num')

    def _setup_file_properties(self):
        self.property_fields = set()
        self.property_template_id = None

        prop_group_name = settings.PROPERTY_GROUP_NAME

        client = self.fileaccess_client_team
        if not hasattr(client, 'file_properties_templates_list_for_team'):
            # NOTE: @ dropbox==8.7.1
            #   AttributeError: 'DropboxTeam' object has no attribute 'file_properties_templates_list_for_team
            client = self.fileaccess_client_team2

        res = client.file_properties_templates_list_for_team()

        REMOVE = False  # WARNING: remove template for debug
        REMOVE_ALL = False  # WARNING: remove all properties template for debug
        if REMOVE:
            for template_id in res.template_ids:
                prop_group = client.file_properties_templates_get_for_team(
                    template_id)
                if REMOVE_ALL is False and prop_group.name != prop_group_name:
                    continue
                # for GRDM
                DEBUG('remove template: ' + template_id)
                client.file_properties_templates_remove_for_team(template_id)
            res = client.file_properties_templates_list_for_team()

        found_template_id = None
        for template_id in res.template_ids:
            prop_group = client.file_properties_templates_get_for_team(
                template_id)
            if prop_group.name != prop_group_name:
                DEBUG('ignored template_id: ' + template_id)
                continue
            # property group for GRDM
            DEBUG('found template_id: ' + template_id)
            found_template_id = template_id
            for field in prop_group.fields:
                self.property_fields.add(field.name)
                # DEBUG('existing prop field: ' + field.name)
            break

        check_keys = []

        # for splited data
        for name, conf in settings.PROPERTY_SPLIT_DATA_CONF.items():
            max_size = float(conf['max_size'])
            num = int(math.ceil(max_size / settings.PROPERTY_MAX_DATA_SIZE))
            check_keys.append(self._prop_split_data_num_key(name))
            for i in range(num):
                key = self._prop_split_key(name, i)
                check_keys.append(key)

        # for simple data
        for key in settings.PROPERTY_KEYS:
            check_keys.append(key)

        add_fields = []
        for key in check_keys:
            if key in self.property_fields:
                continue  # existing field
            f = dropbox.file_properties.PropertyFieldTemplate(
                key, '',
                dropbox.file_properties.PropertyType.string)
            add_fields.append(f)
            DEBUG('new prop field: ' + key)

        if found_template_id is None:
            DEBUG('create new prop fieldss')
            res = client.file_properties_templates_add_for_team(
                prop_group_name, prop_group_name,
                add_fields)
            self.property_template_id = res.template_id
        elif len(add_fields) > 0:
            DEBUG('add prop fields')
            res = client.file_properties_templates_update_for_team(
                found_template_id, prop_group_name, prop_group_name,
                add_fields)
            self.property_template_id = res.template_id
        else:
            DEBUG('not update prop fields: ' + found_template_id)
            self.property_template_id = found_template_id

        DEBUG('property_template_id: ' + self.property_template_id)

    def _update_file_properties(self, team_folder_id, path, properties):
        DEBUG(u'_update_file_properties: team_folder_id={}, path={}'.format(team_folder_id, path))
        template_id = self.property_template_id
        old_properties = self._get_file_properties(team_folder_id, path)
        old_properties.update(properties)
        new_properties = old_properties
        add_or_update_fields = []

        # for splited data
        for name, conf in settings.PROPERTY_SPLIT_DATA_CONF.items():
            data = new_properties.get(name)
            if data is None:
                continue
            max_size = int(conf['max_size'])
            if len(data) > max_size:
                logger.error('too large property: path={}, prop name={}'.format(path, name))
                continue
            data_b64 = base64.b64encode(data)

            def slice_string(s, size):
                return [s[i: i + size] for i in range(0, len(s), size)]

            split_values = slice_string(data_b64,
                                        settings.PROPERTY_MAX_DATA_SIZE)
            add_or_update_fields.append(
                dropbox.file_properties.PropertyField(
                    self._prop_split_data_num_key(name),
                    str(len(split_values))))
            for i, value in enumerate(split_values):
                key = self._prop_split_key(name, i)
                field = dropbox.file_properties.PropertyField(key, value)
                add_or_update_fields.append(field)
                DEBUG('update property: key={}'.format(key))

        # for simple data
        for key in settings.PROPERTY_KEYS:
            value = new_properties.get(key)
            if value:
                add_or_update_fields.append(
                    dropbox.file_properties.PropertyField(
                        key, str(value)))
                DEBUG('update property: key={}'.format(key))

        property_groups = [
            dropbox.file_properties.PropertyGroup(
                template_id,
                fields=add_or_update_fields)]
        client = self.fileaccess_client_user_with_path_root(
            self.admin_dbmid, team_folder_id)
        client.file_properties_properties_overwrite(
            path, property_groups)
        DEBUG(u'file_properties_properties_overwrite(path={}): done'.format(path))

    def _get_file_properties(self, team_folder_id, path):
        DEBUG(u'_get_file_properties: team_folder_id={}, path={}'.format(team_folder_id, path))
        template_id = self.property_template_id
        client = self.fileaccess_client_admin_with_path_root(team_folder_id)
        meta = client.files_get_metadata(
            path,
            include_property_groups=dropbox.file_properties.TemplateFilterBase.filter_some([template_id]))
        if not isinstance(meta, dropbox.files.FileMetadata):
            DEBUG(u'is not a FILE: ' + path)
            return None

        raw_properties = {}
        for prop_group in meta.property_groups:
            if prop_group.template_id != template_id:
                continue
            for field in prop_group.fields:
                raw_properties[field.name] = field.value
                # DEBUG(u'raw_properties[{}] = {}'.format(field.name, field.value))

        result_properties = {}

        # for splited data
        for name, conf in settings.PROPERTY_SPLIT_DATA_CONF.items():
            num = raw_properties.get(self._prop_split_data_num_key(name))
            if num is None:
                continue
            split_values = []
            for i in range(int(num)):
                key = self._prop_split_key(name, i)
                val = raw_properties.get(key)
                if val is None:
                    DEBUG(u'not found: ' + key)
                    break
                split_values.append(val)
                # DEBUG('split data: {}={}'.format(key, val))
                DEBUG('split data key: {}'.format(key))
            data_b64 = ''.join(split_values)
            data = base64.b64decode(data_b64)
            result_properties[name] = data

        # for simple data
        for key in settings.PROPERTY_KEYS:
            data = raw_properties.get(key)
            if data:
                result_properties[key] = data
                DEBUG('simple data: {}={}'.format(key, data))

        return result_properties

    def set_timestamp(self, team_folder_id, path, timesamp_data, timestamp_status):
        properties = {
            'timestamp': timesamp_data,
            settings.PROPERTY_KEY_TIMESTAMP_STATUS: str(timestamp_status)
        }
        self._update_file_properties(team_folder_id, path, properties)

    # return (timestamp_data, timestamp_status, context)
    def get_timestamp(self, team_folder_id, path):
        try:
            properties = self._get_file_properties(team_folder_id, path)
        except ApiError as e:
            properties = None
            if not isinstance(e.error, dropbox.files.GetMetadataError):
                logger.exception(u'unexpected error: team_folder_id={}, path={}'.format(team_folder_id, path))
            else:
                DEBUG('GetMetadataError: {}'.format(e.error.get_path()))
        except Exception:
            logger.exception(u'unexpected error: team_folder_id={}, path={}'.format(team_folder_id, path))
            properties = None
        if properties:
            status = properties.get(settings.PROPERTY_KEY_TIMESTAMP_STATUS)
            try:
                status = int(status)
            except Exception:
                status = None
            return (properties.get('timestamp'), status, self)
        else:
            return (None, None, None)


class FileAttr(object):
    OPTYPE_UNKNOWN = 0
    OPTYPE_FILE = 1
    OPTYPE_DIR = 2
    OPTYPE_DELETED = 3

    def __init__(self, team_info, ent):
        self.team_info = team_info
        self.path_display = ent.path_display
        self.optype = self.OPTYPE_UNKNOWN
        self.modified_by = None  # email

        path = u'{}, path_display={}'.format(
            ent.path_lower, ent.path_display)
        p = 'ignored type'
        sharing_info = None
        if isinstance(ent, dropbox.files.FileMetadata):
            sharing_info = ent.sharing_info
            p = u'[FILE] {}, content_hash={}'.format(
                path, ent.content_hash)
            self.optype = self.OPTYPE_FILE
        elif isinstance(ent, dropbox.files.FolderMetadata):
            sharing_info = ent.sharing_info
            p = u'[DIR] {}, id={}, shared_folder_id={}'.format(
                path, ent.id, ent.shared_folder_id)
            self.optype = self.OPTYPE_DIR
        elif isinstance(ent, dropbox.files.DeletedMetadata):
            p = u'[DELETED] {}'.format(path)
            self.optype = self.OPTYPE_DELETED
            # no sharing_info

        if sharing_info is not None:
            psf_id = sharing_info.parent_shared_folder_id
            p += ', parent_sharing_folder_id={}'.format(psf_id)
            tf = team_info.team_folders.get(psf_id)
            if tf:
                p += u', team_folder_name={}'.format(tf.metadata.name)
            else:
                p += ', <IN NOT A TEAM FOLDER>'

            if self.optype == self.OPTYPE_FILE:
                dbid = sharing_info.modified_by
                self.modified_by = team_info.dbid_to_email.get(dbid)
                p += ', modified_by=(dbid={}, email={})'.format(
                    dbid, self.modified_by)
        DEBUG(p)

    # return (team_folder_id, team_folder_name, subpath)
    def team_folder_path(self):
        # NOTE: team_folder name is path_display.
        p = self.path_display
        team_folder_name = None
        while True:
            head, tail = os.path.split(p)  # dirname + basename
            if head == '/':
                team_folder_name = tail
                break
            p = head
        if team_folder_name is None:
            return None
        tf = self.team_info.team_folder_names.get(team_folder_name)
        if tf is None:
            return None
        subpath = self.path_display[len(u'/' + team_folder_name):]
        return (tf.team_folder_id, team_folder_name, subpath)


PROVIDER_NAME = 'dropboxbusiness'

def _select_admin(node):
    # select from admin contributors
    for user in node.contributors.all():
        if user.is_disabled or user.eppn is None:
            continue
        if node.is_admin_contributor(user):
            DEBUG('selected user for timestamp: username={}, eppn={}, eppn_to_email={}'.format(user.username, user.eppn, eppn_to_email(user.eppn)))
            return user
    raise Exception('unexpected condition')

def _check_and_add_timestamp(team_info, file_attr):
    from addons.dropboxbusiness.models import NodeSettings

    tfp = file_attr.team_folder_path()
    if tfp is None:
        return
    team_folder_id, name, path = tfp
    DEBUG(u'team_folder_id={}, name={}, path={}'.format(team_folder_id,
                                                        name, path))

    def _file_exists(cls, target, path):
        # see osf.models.files/BaseFileNode.get_or_create()
        content_type = ContentType.objects.get_for_model(target)
        kwargs = {'target_object_id': target.id,
                  'target_content_type': content_type,
                  '_path': '/' + path.lstrip('/')}
        return cls.objects.filter(**kwargs).exists()

    def _check_for_file(addon):
        node = addon.owner
        if node.is_deleted:
            return
        admin = _select_admin(node)
        admin_cookie = admin.get_or_create_cookie().decode()
        created = True

        cls = BaseFileNode.resolve_class(PROVIDER_NAME, BaseFileNode.FILE)
        if _file_exists(cls, node, path):
            created = False
        file_node = cls.get_or_create(node, path)
        waterbutler_json_res = waterbutler.get_node_info(
            admin_cookie, node._id, PROVIDER_NAME, path)
        if waterbutler_json_res is None:
            DEBUG(u'waterbutler.get_node_info() is None: path={}'.format(path))
            return
        file_data = waterbutler_json_res.get('data')
        if file_data is None:
            DEBUG(u'waterbutler.get_node_info().get("data") is None: path={}'.format(path))
            return
        DEBUG(u'file_data: ' + str(file_data))
        attrs = file_data['attributes']
        file_node.update(None, attrs, user=admin)  # update content_hash
        file_info = {
            'file_id': file_node._id,
            'file_name': attrs.get('name'),
            'file_path': attrs.get('materialized'),
            'size': attrs.get('size'),
            'created': attrs.get('created_utc'),
            'modified': attrs.get('modified_utc'),
            'file_version': '',
            'provider': PROVIDER_NAME
        }
        # verified by admin
        verify_result = timestamp.check_file_timestamp(
            admin.id, node, file_info, verify_external_only=True)
        DEBUG('check timestamp: verify_result={}'.format(verify_result.get('verify_result_title')))
        if verify_result['verify_result'] == \
           api_settings.TIME_STAMP_TOKEN_CHECK_SUCCESS:
            return  # already checked

        # The file is created (new file) or modified.
        user = None
        if file_attr.modified_by:
            eppn = email_to_eppn(file_attr.modified_by)
            if eppn:
                try:
                    user = OSFUser.objects.get(eppn=eppn)
                except OSFUser.DoesNotExist:
                    logger.warning(u'modified by unknown user: email={}'.format(file_attr.modified_by))
        metadata = {
            'path': path
        }
        if created:
            action = 'file_added'
        else:
            action = 'file_updated'
        if user:  # modified by user
            verify_result = timestamp.add_token(user.id, node, file_info)
            addon.create_waterbutler_log(Auth(user), action, metadata)
            # timestamp.add_log_a_file(NodeLog.TIMESTAMP_ADDED, node, user.id, PROVIDER_NAME, file_node._id)
        else:  # modified by unknown user
            verify_result = timestamp.add_token(admin.id, node, file_info)
            addon.create_waterbutler_log(None, action, metadata)
            # timestamp.add_log_a_file(NodeLog.TIMESTAMP_ADDED, node, admin.id, PROVIDER_NAME, file_node._id)
        logger.info(u'update timestamp by Webhook for Dropbox Business: node_guid={}, path={}, verify_result={}'.format(node._id, path, verify_result.get('verify_result_title')))

    def _check_for_folder(addon):
        logger.info(u'folder created: path={}, path_display={}'.format(path, file_attr.path_display))
        metadata = {
            'path': path
        }
        addon.create_waterbutler_log(None, 'folder_created', metadata)

    def _deleted_entry(addon):
        logger.info(u'deleted: path={}, path_display={}'.format(path, file_attr.path_display))
        metadata = {
            'path': path
        }
        addon.create_waterbutler_log(None, 'file_removed', metadata)

    # team_folder_id of NodeSettings is not UNIQUE,
    # but two or more NodeSettings do not exist.
    with transaction.atomic():
        for addon in NodeSettings.objects.filter(
                team_folder_id=team_folder_id):
            try:
                if file_attr.optype == FileAttr.OPTYPE_FILE:
                    _check_for_file(addon)
                ### unable to distinguish updating event from GRDM or Dropbox
                # elif file_attr.optype == FileAttr.OPTYPE_DIR:
                #     _check_for_folder(addon)
                # elif file_attr.optype == FileAttr.OPTYPE_DELETED:
                #     _deleted_entry(addon)
            except Exception:
                logger.exception('project guid={}'.format(addon.owner._id))
    # Unknown team_folder_id is ignored.

def team_id_to_instituion(team_id):
    try:
        ea = ExternalAccount.objects.get(
            provider=PROVIDER_NAME, provider_id=team_id)
        opt = RdmAddonOption.objects.get(
            provider=PROVIDER_NAME, external_accounts=ea)
        return opt.institution
    except Exception:
        return None

@celery_app.task(bind=True, base=AbortableTask)
def celery_check_updated_files(self, team_ids):
    # avoid "ImportError: cannot import name"
    from addons.dropboxbusiness.models import DropboxBusinessManagementProvider

    def _check_team_files(dbtid):
        ea = ExternalAccount.objects.get(
            provider=PROVIDER_NAME, provider_id=dbtid)
        opt = RdmAddonOption.objects.get(
            provider=PROVIDER_NAME, external_accounts=ea)
        if opt.extended is None:
            opt.extended = {}

        management_opt = get_rdm_addon_option(
            opt.institution._id, DropboxBusinessManagementProvider.short_name,
            create=False)
        fileaccess_token = addon_option_to_token(opt)
        management_token = addon_option_to_token(management_opt)

        KEY_ADMIN_ID = 'admin_dbmid'
        KEY_LIST_CURSOR = 'list_cursor'
        admin_dbmid = opt.extended.get(KEY_ADMIN_ID, None)
        list_cursor = opt.extended.get(KEY_LIST_CURSOR, None)

        team_info = TeamInfo(fileaccess_token, management_token, admin=True)
        # Dropbox Team Admin is changed
        if admin_dbmid != team_info.admin_dbmid:
            admin_dbmid = team_info.admin_dbmid
            opt.extended[KEY_ADMIN_ID] = admin_dbmid
            list_cursor = None
        files, cursor = team_info.list_updated_files(list_cursor)
        for file_attr in files:
            _check_and_add_timestamp(team_info, file_attr)
        opt.extended[KEY_LIST_CURSOR] = cursor
        opt.save()

    if not lock.LOCK_RUN.trylock():
        lock.add_plan(team_ids)
        return  # exit

    while True:
        team_ids = lock.get_plan(team_ids)
        if len(team_ids) == 0:
            break
        # to wait for updating timestamp in create_waterbutler_log()
        time.sleep(5)
        for dbtid in team_ids:
            institution = team_id_to_instituion(dbtid)
            name = u'Institution={}, Dropbox Business Team ID={}'.format(
                institution, dbtid)
            try:
                DEBUG(u'check and update timestamp: {}'.format(name))
                _check_team_files(dbtid)
            except Exception:
                logger.exception(name)
        team_ids = []

    lock.LOCK_RUN.unlock()
