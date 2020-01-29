"""Script to verify permissions have transferred post groups/guardian.

"docker-compose run --rm web python3 -m scripts.remove_after_use.verify_groups_guardian_migration"
"""
import logging
from random import randint

from website.app import setup_django
setup_django()

from django.apps import apps
from django.contrib.auth.models import Permission, Group

from osf.utils.permissions import PERMISSIONS, reduce_permissions
from osf.models import AbstractNode, Contributor, Preprint, Node, Registration, QuickFilesNode
from osf.models.node import NodeGroupObjectPermission
from osf.models.preprint import PreprintGroupObjectPermission
from osf.utils.permissions import READ, WRITE, ADMIN

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def check_expected(expected, actual, error_msg):
    if expected != actual:
        logger.info('{}. Expected {} rows migrated; received {}.'.format(error_msg, expected, actual))
    else:
        logger.info('{} rows added.'.format(actual))

def verify_permissions_created():
    """
    Expecting three permissions added, read, write, admin perms
    """
    expected = len(PERMISSIONS)
    actual = Permission.objects.filter(codename__in=PERMISSIONS).count()

    check_expected(expected, actual, 'Discepancy in Permission table.')

def verify_auth_groups():
    """
    Expecting three groups added for every AbstractNode - read/write/admin
    """
    expected = AbstractNode.objects.count() * 3
    actual = Group.objects.filter(name__icontains='node_').count()

    check_expected(expected, actual, 'Discepancy in auth_group table.')

def verify_expected_node_group_object_permission_counts():
    """
    For every AbstactNode, three Django groups - admin, write, read are created.
    Admin group gets admin/write/read perms, write - write/read, and read: read.
    So for every node, 6 line items added to NodeGroupObjectPermission.  Linking
    these groups with their permissions to the given node.
    """
    expected_nodegroupobjperm_count = AbstractNode.objects.count() * 6
    actual_nodegroupobjperm_count = NodeGroupObjectPermission.objects.count()

    check_expected(expected_nodegroupobjperm_count, actual_nodegroupobjperm_count, 'Discrepancy in NodeGroupObjectPermission table.')

def verify_expected_contributor_migration():
    """
    Based on contributor admin/write/read columns, users are migrated to the osfgroupuser table and added to the appropriate Django group.
    """
    OSFUserGroup = apps.get_model('osf', 'osfuser_groups')
    expected = Contributor.objects.count()
    actual = OSFUserGroup.objects.filter(group__name__icontains='node_').count()
    check_expected(expected, actual, 'Discrepancy in contributor migration to OSFUserGroup table.')

def verify_preprint_foreign_key_migration():
    expected_preprintgroupobjperm_count = Preprint.objects.count() * 6
    actual_preprintgroupobjperm_count = PreprintGroupObjectPermission.objects.count()

    check_expected(expected_preprintgroupobjperm_count, actual_preprintgroupobjperm_count, 'Discrepancy in PreprintGroupObjectPermission table.')

def verify_random_objects():
    resources = [Node, Registration, QuickFilesNode]
    for resource in resources:
        for i in range(1,10):
            random_resource = _get_random_object(resource)
            if random_resource:
                _verify_contributor_perms(random_resource)

def _verify_contributor_perms(resource):
    for user in resource.contributors:
        contrib = Contributor.objects.get(node=resource, user=user)

        if contrib.admin:
            if contrib.permission != ADMIN:
                _suspected_contributor_migration_error(contrib)
        elif contrib.write:
            if contrib.permission != WRITE:
                _suspected_contributor_migration_error(contrib)
        elif contrib.read:
            if contrib.permission != READ:
                _suspected_contributor_migration_error(contrib)


def _suspected_contributor_migration_error(contrib):
    logger.info('Suspected contributor migration error on {}.'.format(contrib._id))


def _get_random_object(model):
    model_count = model.objects.count()
    if model_count:
        return model.objects.all()[randint(1, model_count - 1)]
    return None


def main():
    logger.info('Verifying permissions created...')
    verify_permissions_created()
    logger.info('Verifying auth groups created...')
    verify_auth_groups()
    logger.info('Verifying node groups given permissions to their nodes...')
    verify_expected_node_group_object_permission_counts()
    logger.info('Verifying contributors added to node django groups...')
    verify_expected_contributor_migration()
    logger.info('Verifying preprint perms migrated to direct foreign key table...')
    verify_preprint_foreign_key_migration()
    logger.info('Verifying a selection of random contributor permissions...')
    verify_random_objects()
    logger.info('Done!')


if __name__ == '__main__':
    main()
