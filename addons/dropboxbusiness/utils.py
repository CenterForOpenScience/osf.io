# -*- coding: utf-8 -*-
import logging
import time

import dropbox
from dropbox.dropbox import DropboxTeam
from dropbox.exceptions import ApiError
from dropbox.sharing import MemberSelector
from dropbox.team import (GroupMembersAddError, GroupMembersRemoveError,
                          GroupSelector, UserSelectorArg, GroupAccessType,
                          MemberAccess)
from addons.dropboxbusiness import settings

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
    """best effort synchronization of members.
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
            # best effort synchronization
            if not isinstance(e.error, GroupMembersAddError) or \
               not e.error.is_users_not_found():
                raise  # reraise

    for memb in remove_member_list:
        try:
            poll_jobs.append(
                manage_client.team_groups_members_remove(group, [memb])
            )
        except ApiError as e:
            # best effort synchronization
            if not isinstance(e.error, GroupMembersRemoveError) or \
               not e.error.is_users_not_found():
                raise  # reraise

    for job in poll_jobs:
        poll_team_groups_job(manage_client, job)


def create_team_folder(
        file_access_token,
        management_access_token,
        admin_dbmid,
        team_folder_name,
        group_name,
        grdm_member_email_list
):
    """
    :raises: dropbox.exceptions.DropboxException
    :returns: (team folder id string, group id string)
    """

    fclient = DropboxTeam(file_access_token)
    mclient = DropboxTeam(management_access_token)

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
