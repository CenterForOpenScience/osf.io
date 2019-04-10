import pytest


from website.project import new_private_link

from .factories import PrivateLinkFactory, NodeFactory
from osf.models import RegistrationSchema, DraftRegistration, NodeLog

@pytest.mark.django_db
def test_factory():
    plink = PrivateLinkFactory()
    assert plink.name
    assert plink.key
    assert plink.creator

# Copied from tests/test_models.py
@pytest.mark.django_db
class TestPrivateLink:

    def test_node_scale(self):
        link = PrivateLinkFactory()
        project = NodeFactory()
        comp = NodeFactory(parent=project)
        link.nodes.add(project)
        link.save()
        assert link.node_scale(project) == -40
        assert link.node_scale(comp) == -20

    # Regression test for https://sentry.osf.io/osf/production/group/1119/
    def test_to_json_nodes_with_deleted_parent(self):
        link = PrivateLinkFactory()
        project = NodeFactory(is_deleted=True)
        node = NodeFactory(parent=project)
        link.nodes.add(project, node)
        link.save()
        result = link.to_json()
        # result doesn't include deleted parent
        assert len(result['nodes']) == 1

    # Regression test for https://sentry.osf.io/osf/production/group/1119/
    def test_node_scale_with_deleted_parent(self):
        link = PrivateLinkFactory()
        project = NodeFactory(is_deleted=True)
        node = NodeFactory(parent=project)
        link.nodes.add(project, node)
        link.save()
        assert link.node_scale(node) == -40

    def test_create_from_node(self):
        proj = NodeFactory()
        user = proj.creator
        schema = RegistrationSchema.objects.first()
        data = {'some': 'data'}
        draft = DraftRegistration.create_from_node(
            proj,
            user=user,
            schema=schema,
            data=data,
        )
        assert user == draft.initiator
        assert schema == draft.registration_schema
        assert data == draft.registration_metadata
        assert proj == draft.branched_from


@pytest.mark.django_db
class TestNodeProperties:

    def test_private_links_active(self):
        link = PrivateLinkFactory()
        deleted = PrivateLinkFactory(is_deleted=True)
        node = NodeFactory()
        link.nodes.add(node)
        deleted.nodes.add(node)
        assert link in node.private_links_active
        assert deleted not in node.private_links_active

    def test_private_link_keys_active(self):
        link = PrivateLinkFactory()
        deleted = PrivateLinkFactory(is_deleted=True)
        node = NodeFactory()
        link.nodes.add(node)
        deleted.nodes.add(node)
        assert link.key in node.private_link_keys_active
        assert deleted.key not in node.private_link_keys_active

    def test_private_link_keys_deleted(self):
        link = PrivateLinkFactory()
        deleted = PrivateLinkFactory(is_deleted=True)
        node = NodeFactory()
        link.nodes.add(node)
        deleted.nodes.add(node)
        assert link.key not in node.private_link_keys_deleted
        assert deleted.key in node.private_link_keys_deleted


@pytest.mark.django_db
class TestPrivateLinkNodeLogs:

    def test_create_private_link_log(self):
        node = NodeFactory()
        new_private_link(
            name='wooo',
            user=node.creator,
            nodes=[node],
            anonymous=False
        )
        last_log = node.logs.latest()

        assert last_log.action == NodeLog.VIEW_ONLY_LINK_ADDED
        assert last_log.params == {
            'node': node._id,
            'project': node.parent_node._id,
            'anonymous_link': False,
            'user': node.creator._id
        }

    def test_create_anonymous_private_link_log(self):
        node = NodeFactory()
        new_private_link(
            name='wooo',
            user=node.creator,
            nodes=[node],
            anonymous=True
        )
        last_log = node.logs.latest()

        assert last_log.action == NodeLog.VIEW_ONLY_LINK_ADDED
        assert last_log.params == {
            'node': node._id,
            'project': node.parent_node._id,
            'anonymous_link': True,
            'user': node.creator._id
        }
