# Raw SQL for migration 0199 to make available for import
add_draft_read_write_admin_auth_groups = """
    INSERT INTO auth_group (name)
    SELECT regexp_split_to_table('draft_registration_' || D.id || '_read,draft_registration_' || D.id || '_write,draft_registration_' || D.id || '_admin', ',')
    FROM osf_draftregistration D;
    """

# Before auth_group items can be deleted, users need to be removed from those auth_groups
remove_draft_auth_groups = """
    DELETE FROM osf_osfuser_groups
    WHERE group_id IN (
    SELECT id FROM auth_group WHERE name LIKE '%draft_registration_%'
    );

    DELETE FROM auth_group WHERE name in
    (SELECT regexp_split_to_table('draft_registration_' || D.id || '_read,draft_registration_' || D.id || '_write,draft_registration_' || D.id || '_admin', ',')
    FROM osf_draftregistration D);
    """

# Forward migration - add read permissions to all draft registration django read groups, add read/write perms
# to all draft registration django write groups, and add read/write/admin perms to all draft registration django admin groups
add_permissions_to_draft_registration_groups = """
    -- Adds "read_draft_registration" permissions to all Draft Reg read groups - uses DraftRegistrationGroupObjectPermission table
    INSERT INTO osf_draftregistrationgroupobjectpermission (content_object_id, group_id, permission_id)
    SELECT D.id as content_object_id, G.id as group_id, PERM.id AS permission_id
    FROM osf_draftregistration AS D, auth_group G, auth_permission AS PERM
    WHERE G.name = 'draft_registration_' || D.id || '_read'
    AND PERM.codename = 'read_draft_registration';

    -- Adds "read_draft_registration" and "write_draft_registration" permissions to all Draft Reg write groups
    INSERT INTO osf_draftregistrationgroupobjectpermission (content_object_id, group_id, permission_id)
    SELECT D.id as content_object_id, G.id as group_id, PERM.id AS permission_id
    FROM osf_draftregistration AS D, auth_group G, auth_permission AS PERM
    WHERE G.name = 'draft_registration_' || D.id || '_write'
    AND (PERM.codename = 'read_draft_registration' OR PERM.codename = 'write_draft_registration');

    -- Adds "read_draft_registration", "write_draft_registration", and "admin_draft_registration" permissions to all Draft Reg admin groups
    INSERT INTO osf_draftregistrationgroupobjectpermission (content_object_id, group_id, permission_id)
    SELECT D.id as content_object_id, G.id as group_id, PERM.id AS permission_id
    FROM osf_draftregistration AS D, auth_group G, auth_permission AS PERM
    WHERE G.name = 'draft_registration_' || D.id || '_admin'
    AND (PERM.codename = 'read_draft_registration' OR PERM.codename = 'write_draft_registration' OR PERM.codename = 'admin_draft_registration');
    """

# Reverse migration - Remove all rows from DraftRegistrationGroupObjectPermission table - table gives draft django groups
# permissions to draft reg
drop_draft_reg_group_object_permission_table = """
    DELETE FROM osf_draftregistrationgroupobjectpermission;
    """
