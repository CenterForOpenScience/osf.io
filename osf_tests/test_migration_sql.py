from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
import pytest

from . import factories
from osf.models import DraftRegistration
from osf.models.registrations import DraftRegistrationGroupObjectPermission
from osf.migrations.sql.draft_nodes_migration import (
    add_draft_read_write_admin_auth_groups,
    remove_draft_auth_groups,
    add_permissions_to_draft_registration_groups,
    drop_draft_reg_group_object_permission_table)

class TestMigrationSQL197:

    @pytest.mark.django_db
    def test_remove_draft_auth_groups(self):
        draft_reg = factories.DraftRegistrationFactory()
        draft_reg.save()
        assert(len(draft_reg.group_objects))
        with connection.cursor() as cursor:
            cursor.execute(drop_draft_reg_group_object_permission_table)
            cursor.execute(remove_draft_auth_groups)
        draft_reg_from_db = DraftRegistration.objects.get(id=draft_reg.id)
        assert(len(draft_reg_from_db.group_objects) == 0)

    @pytest.mark.django_db
    def test_add_draft_read_write_admin_auth_groups(self):
        with connection.cursor() as cursor:
            cursor.execute(drop_draft_reg_group_object_permission_table)
            cursor.execute(remove_draft_auth_groups)
            cursor.execute(add_draft_read_write_admin_auth_groups)
        draft_reg = factories.DraftRegistrationFactory()
        draft_reg.save()
        assert(len(draft_reg.group_objects))

    @pytest.mark.django_db
    def test_drop_draft_reg_group_object_permission_table(self):
        draft_registration = factories.DraftRegistrationFactory()
        draft_registration.save()
        draft_reg_group_obj_perm = DraftRegistrationGroupObjectPermission.objects.filter(content_object=draft_registration)[0]
        draft_reg_group_obj_perm_id = draft_reg_group_obj_perm.id
        with connection.cursor() as cursor:
            cursor.execute(drop_draft_reg_group_object_permission_table)
        with pytest.raises(ObjectDoesNotExist):
            DraftRegistrationGroupObjectPermission.objects.get(id=draft_reg_group_obj_perm_id)

    @pytest.mark.django_db
    def test_add_permissions_to_draft_registration_groups(self):
        with connection.cursor() as cursor:
            cursor.execute(drop_draft_reg_group_object_permission_table)
            cursor.execute(add_permissions_to_draft_registration_groups)
        draft_reg = factories.DraftRegistrationFactory()
        draft_reg.save()
        assert(DraftRegistrationGroupObjectPermission.objects.filter(content_object=draft_reg).exists())
