import pytest
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    NodeFactory,
)
from osf.models import NodeRelation
from osf.utils import permissions

@pytest.fixture()
def admin_contrib():
    return AuthUserFactory()

@pytest.fixture()
def write_contrib():
    return AuthUserFactory()

@pytest.fixture()
def read_contrib():
    return AuthUserFactory()

@pytest.fixture()
def project(admin_contrib, write_contrib, read_contrib):
    project = ProjectFactory(creator=admin_contrib)
    project.add_contributor(write_contrib, permissions.WRITE)
    project.add_contributor(read_contrib, permissions.READ)
    project.save()
    return project

@pytest.fixture()
def url(project):
    return f'/{API_BASE}nodes/{project._id}/reorder_components/'


@pytest.mark.django_db
class TestNodeReorderComponents:

    @pytest.fixture()
    def children(self, project, admin_contrib):
        child1 = NodeFactory(parent=project, is_public=False, creator=admin_contrib)
        child2 = NodeFactory(parent=project, is_public=False, creator=admin_contrib)
        child3 = NodeFactory(parent=project, is_public=True, creator=admin_contrib)

        rel1 = NodeRelation.objects.get(parent=project, child=child1)
        rel2 = NodeRelation.objects.get(parent=project, child=child2)
        rel3 = NodeRelation.objects.get(parent=project, child=child3)
        project.set_noderelation_order([rel2.pk, rel3.pk, rel1.pk])

        return [child1, child2, child3]

    @pytest.fixture
    def payload_asc(self, children):
        return {
            'data': [
                {
                    'type': 'nodes',
                    'id': each._id,
                    'attributes': {
                        '_order': pos
                    }
                } for pos, each in enumerate(children)
            ]
        }

    @pytest.fixture
    def payload_desc(self, children):
        return {
            'data': [
                {
                    'type': 'nodes',
                    'id': each._id,
                    'attributes': {
                        '_order': pos
                    }
                } for pos, each in enumerate(children[::-1])
            ]
        }

    def test_reorder_components_admin(
            self, app, project, admin_contrib, children, url, payload_asc, payload_desc
    ):
        res = app.patch_json_api(url, payload_asc, auth=admin_contrib.auth, expect_errors=True, bulk=True)
        project.reload()
        component_order = [el.child._id for el in project.node_relations.all()]
        assert res.status_code == 200
        assert component_order == [each._id for each in children]

        res = app.put_json_api(url, payload_desc, auth=admin_contrib.auth, expect_errors=True, bulk=True)
        project.reload()
        component_order = [el.child._id for el in project.node_relations.all()]
        assert res.status_code == 200
        assert component_order == [each._id for each in children[::-1]]

    def test_reorder_components_write_read(
            self, app, write_contrib, read_contrib, url, payload_asc
    ):
        res = app.patch_json_api(url, payload_asc, auth=write_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 403

        res = app.patch_json_api(url, payload_asc, auth=read_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 403

    def test_reorder_invalid_component(
            self, app, project, admin_contrib, url, payload_asc
    ):
        payload_asc['data'][0]['id'] = '12345'
        res = app.patch_json_api(url, payload_asc, auth=admin_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == f'The 12345 node is not a component of the {project._id} node'

    def test_reorder_component_different_order(
            self, app, project, admin_contrib, url, payload_asc
    ):
        payload_asc['data'][0]['id'] = '12345'
        payload_asc['data'][1]['id'] = '12345'
        res = app.patch_json_api(url, payload_asc, auth=admin_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Item 12345 appears multiple times with different _order values.'

    def test_reorder_component_same_order(
            self, app, project, admin_contrib, url, payload_asc
    ):
        payload_asc['data'][0]['id'] = '12345'
        payload_asc['data'][0]['attributes']['_order'] = 1
        payload_asc['data'][1]['id'] = '12345'
        payload_asc['data'][1]['attributes']['_order'] = 1
        res = app.patch_json_api(url, payload_asc, auth=admin_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Item 12345 appears multiple times with the same _order value.'

    def test_reorder_component_invalid_order(
            self, app, project, admin_contrib, url, payload_asc
    ):
        payload_asc['data'][0]['attributes']['_order'] = -1
        res = app.patch_json_api(url, payload_asc, auth=admin_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == f'Item {payload_asc['data'][0]['id']} has _order -1 which is lower than zero.'

        payload_asc['data'][0]['attributes']['_order'] = 5
        res = app.patch_json_api(url, payload_asc, auth=admin_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == f'Item {payload_asc['data'][0]['id']} has _order 5 which is higher than the list length.'

    def test_reorder_multiple_components_same_order(
            self, app, project, admin_contrib, url, payload_asc
    ):
        payload_asc['data'][0]['attributes']['_order'] = 1
        payload_asc['data'][1]['attributes']['_order'] = 1
        res = app.patch_json_api(url, payload_asc, auth=admin_contrib.auth, expect_errors=True, bulk=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Multiple items have the same _order value 1.'
