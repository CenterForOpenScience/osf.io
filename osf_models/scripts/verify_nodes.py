from website.models import Node as MODMNode
from website.models import Tag as MODMTag
from framework.auth import User as MODMUser
from modularodm import Q
import gc
from framework.guid.model import Guid as MODMGuid

from website.app import init_app
from osf_models.models import Node, User, Tag, Guid, Contributor


def verify_contributors(node, modm_node):
    for modm_contributor in modm_node.contributors:
        try:
            contributor = node.contributor_set.get(
                user___guid__guid=modm_contributor._id)
            assert contributor.user._guid.guid == modm_contributor._id, 'ID mismatch...'

            # permissions
            assert contributor.write == (
                'write' in modm_node.permissions[modm_contributor._id]
            ), 'Write permission for contributor with id {} doesn\'t match'.format(
                contributor.id)
            assert contributor.read == (
                'read' in modm_node.permissions[modm_contributor._id]
            ), 'Read permission for contributor with id {} doesn\'t match'.format(
                contributor.id)
            assert contributor.admin == (
                'admin' in modm_node.permissions[modm_contributor._id]
            ), 'Admin permission for contributor with id {} doesn\'t match'.format(
                contributor.id)
            assert contributor.visible == (
                contributor.user._guid.guid in
                modm_node.visible_contributor_ids
            ), 'Visibility for contributor with id {} doesn\'t match'.format(
                contributor.id)
        except Contributor.DoesNotExist:
            print 'Contributor {} exists in MODM but not in django on node {}'.format(
                modm_contributor._id, node._guid.guid)


def verify_tags(node, modm_node):
    modm_tag_keys = sorted(set(modm_node.tags._to_primary_keys()))
    django_tag_keys = sorted(set(node.tags.filter(
        system=False).values_list('_id',
                                  flat=True)))
    modm_system_tag_keys = sorted(set(modm_node.system_tags))
    django_system_tag_keys = sorted(set(
        node.system_tags.values_list('_id',
                                     flat=True)))

    assert modm_tag_keys == django_tag_keys, 'Modm tags {} don\'t match django tags {}'.format(
        modm_tag_keys, django_tag_keys)
    assert modm_system_tag_keys == django_system_tag_keys, 'Modm system tag keys {} don\'t match django system tags {}'.format(
        modm_system_tag_keys, django_system_tag_keys)


def main():
    nodes = Node.objects.all()
    total = len(nodes)
    count = 0

    for node in nodes:
        modm_node = MODMNode.load(node._guid.guid)
        verify_contributors(node, modm_node)
        verify_tags(node, modm_node)
        count += 1

        if count % (total * .001) == 0:
            floatal = float(total)
            flount = float(count)
            print 'Verified nodes {}%'.format((
                (floatal - flount) / floatal - 1.0) * -100.0)

        # clear out
        modm_node = None
        node = None
        floatal = None
        flount = None

        if count % 1000 == 0:
            garbage = gc.collect()
            print '{}:{} Collected {} whole garbages...'.format(count, total,
                                                                garbage)
