import pytest

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory
)

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.mark.django_db
class TestExceptionFormatting:

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_no_title(self):
        return {
            'data': {
                'attributes': {
                    'description': 'A Monument to Reason',
                    'category': 'data',
                    'type': 'nodes',
                }
            }
        }

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/'.format(API_BASE, private_project._id)

    def test_exception_formatting(self, app, user, non_contrib, public_project, private_project, private_url, project_no_title):

    #   test_creates_project_with_no_title_formatting
        url = '/{}nodes/'.format(API_BASE)
        res = app.post_json_api(url, project_no_title, auth=user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert res.json['errors'][0]['source'] == {'pointer': '/data/attributes/title'}
        assert res.json['errors'][0]['detail'] == 'This field is required.'

    #   test_node_does_not_exist_formatting
        url = '/{}nodes/{}/'.format(API_BASE, '12345')
        res = app.get(url, auth=user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert errors[0] == {'detail': 'Not found.'}

    #   test_forbidden_formatting
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert errors[0] == {'detail': 'You do not have permission to perform this action.'}

    #   test_not_authorized_formatting
        res = app.get(private_url, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert errors[0] == {'detail': 'Authentication credentials were not provided.'}

    #   test_update_project_with_no_title_or_category_formatting
        res = app.put_json_api(private_url, {'data': {'type': 'nodes', 'id': private_project._id, 'attributes': {'description': 'New description'}}}, auth=user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert len(errors) == 2
        errors = res.json['errors']
        assert errors[0]['source'] == {'pointer': '/data/attributes/category'}
        assert errors[1]['source'] == {'pointer': '/data/attributes/title'}

        assert errors[0]['detail'] == 'This field is required.'
        assert errors[1]['detail'] == 'This field is required.'

    #   test_create_node_link_no_target_formatting
        url = private_url + 'node_links/'
        res = app.post_json_api(url, {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': '',
                            'type': 'nodes',
                        }
                    }
                }
            }
        }, auth=user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert res.status_code == 400
        assert res.json['errors'][0]['source'] == {'pointer': '/data/id'}
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'

    #   test_node_link_already_exists
        url = private_url + 'node_links/'
        res = app.post_json_api(url, {
            'data': {
                'type': 'node_links',
                'relationships': {
                    'nodes': {
                        'data': {
                            'id': public_project._id,
                            'type': 'nodes',
                        }
                    }
                }
            }
        }, auth=user.auth)
        assert res.status_code == 201

        res = app.post_json_api(url, {'data': {
            'type': 'node_links',
            'relationships': {
                'nodes': {
                    'data': {
                        'id': public_project._id,
                        'type': 'nodes'
                    }
                }
            }
        }}, auth=user.auth, expect_errors=True)
        errors = res.json['errors']
        assert(isinstance(errors, list))
        assert res.status_code == 400
        assert(public_project._id in res.json['errors'][0]['detail'])
