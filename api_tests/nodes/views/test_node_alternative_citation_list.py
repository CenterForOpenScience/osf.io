import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    AlternativeCitationFactory,
)
from rest_framework import exceptions
from website.util import permissions


@pytest.fixture()
def payload():
    def make_payload(name=None, text=None):
        data = {'data': {
            'type': 'citations',
            'attributes': {}
            }
        }
        if name is not None:
            data['data']['attributes']['name'] = name
        if text is not None:
            data['data']['attributes']['text'] = text
        return data
    return make_payload

@pytest.fixture()
def payload_citation(payload):
    return payload(name='name', text='text')

@pytest.fixture()
def payload_repeat_name(payload):
    return payload(name='name', text='Citation')

@pytest.fixture()
def payload_repeat_text(payload):
    return payload(name='Citation', text='text')

@pytest.fixture()
def payload_no_name(payload):
    return payload(text='text')

@pytest.fixture()
def payload_no_text(payload):
    return payload(name='name')

@pytest.fixture()
def payload_empty(payload):
    return payload()

@pytest.fixture()
def create_project():
    def new_project(creator, public=True, contrib=None, citation=False, registration=False):
        project = ProjectFactory(creator=creator, is_public=public)
        if contrib:
            project.add_contributor(contrib, permissions=[permissions.READ, permissions.WRITE], visible=True)
        if citation:
            citation = AlternativeCitationFactory(name='name', text='text')
            project.alternative_citations.add(citation)
        project.save()
        if registration:
            registration = RegistrationFactory(project=project, is_public=public)
            return registration
        return project
    return new_project

@pytest.mark.django_db
class TestCreateAlternativeCitations:

    @pytest.fixture()
    def req(self, app, create_project):
        def make_req(data, errors=False, is_admin=False, is_contrib=True, logged_out=False, **kwargs):
            admin = AuthUserFactory()
            registration = kwargs.get('registration', None)
            if is_admin:
                user = admin
            elif not logged_out:
                user = AuthUserFactory()
                kwargs['contrib'] = user if is_contrib else None
            project = create_project(admin, **kwargs)
            if registration:
                project_url = '/{}registrations/{}/citations/'.format(API_BASE, project._id)
            else:
                project_url = '/{}nodes/{}/citations/'.format(API_BASE, project._id)
            if not logged_out:
                res = app.post_json_api(project_url, data, auth=user.auth, expect_errors=errors)
            else:
                res = app.post_json_api(project_url, data, expect_errors=errors)
            return res, project
        return make_req

    def test_add_citation_admin_public(self, req, payload_citation):
        res, project = req(payload_citation, is_admin=True)
        assert res.status_code == 201
        assert res.json['data']['attributes']['name'] == payload_citation['data']['attributes']['name']
        assert res.json['data']['attributes']['text'] == payload_citation['data']['attributes']['text']
        project.reload()
        assert project.alternative_citations.count() == 1

    def test_add_citation_admin_private(self, req, payload_citation):
        res, project = req(payload_citation, is_admin=True, public=False)
        assert res.status_code == 201
        assert res.json['data']['attributes']['name'] == payload_citation['data']['attributes']['name']
        assert res.json['data']['attributes']['text'] == payload_citation['data']['attributes']['text']
        project.reload()
        assert project.alternative_citations.count() == 1

    def test_add_citation_and_auth_errors(self, req, payload_citation):

    #   test_add_citation_non_admin_public
        res, project = req(payload_citation, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_citation_non_admin_private
        res, project = req(payload_citation, public=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_citation_non_contrib_public
        res, project = req(payload_citation, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_citation_non_contrib_private
        res, project = req(payload_citation, public=False, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_citation_logged_out_public
        res, project = req(payload_citation, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_citation_logged_out_private
        res, project = req(payload_citation, public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_repeat_name_and_text_admin_public
        res, project = req(payload_citation, citation=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        errors = [error['detail'] for error in res.json['errors']]
        assert 'There is already a citation named \'name\'' in errors
        assert 'Citation matches \'name\'' in errors
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_and_text_admin_private
        res, project = req(payload_citation, public=False, citation=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        errors = [error['detail'] for error in res.json['errors']]
        assert 'There is already a citation named \'name\'' in errors
        assert 'Citation matches \'name\'' in errors
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_and_text_non_admin_public
        res, project = req(payload_citation, citation=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_and_text_non_admin_private
        res, project = req(payload_citation, public=False, citation=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_and_text_non_contrib_public
        res, project = req(payload_citation, citation=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_and_text_non_contrib_private
        res, project = req(payload_citation, public=False, citation=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_and_text_logged_out_public
        res, project = req(payload_citation, citation=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_and_text_logged_out_private
        res, project = req(payload_citation, public=False, citation=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_citation_admin_public_reg(self):
        res, registration = req(payload_citation, registration=True, is_admin=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 0

    #   test_add_citation_admin_private_reg(self):
        res, registration = req(payload_citation, public=False, registration=True, is_admin=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 0

    #   test_add_citation_non_admin_public_reg(self):
        res, registration = req(payload_citation, registration=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 0

    #   test_add_citation_non_admin_private_reg(self):
        res, registration = req(payload_citation, public=False, registration=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 0

    #   test_add_citation_non_contrib_public_reg(self):
        res, registration = req(payload_citation, registration=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 0

    #   test_add_citation_non_contrib_private_reg(self):
        res, registration = req(payload_citation, public=False, registration=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 0

    #   test_add_citation_logged_out_public_reg(self):
        res, registration = req(payload_citation, registration=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        assert registration.alternative_citations.count() == 0

    #   test_add_citation_logged_out_private_reg(self):
        res, registration = req(payload_citation, public=False, registration=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        assert registration.alternative_citations.count() == 0

    def test_add_repeat_name_errors(self, req, payload_repeat_name):

    #   test_add_repeat_name_admin_public
        res, project = req(payload_repeat_name, citation=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'There is already a citation named \'name\''
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_admin_private
        res, project = req(payload_repeat_name, public=False, citation=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'There is already a citation named \'name\''
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_non_admin_public
        res, project = req(payload_repeat_name, citation=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_non_admin_private
        res, project = req(payload_repeat_name, public=False, citation=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_non_contrib_public
        res, project = req(payload_repeat_name, citation=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_non_contrib_private
        res, project = req(payload_repeat_name, public=False, is_contrib=False, citation=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_logged_out_public
        res, project = req(payload_repeat_name, citation=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_name_logged_out_private
        res, project = req(payload_repeat_name, public=False, citation=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    def test_add_repeat_text_errors(self, req, payload_repeat_text):

    #   test_add_repeat_text_admin_public
        res, project = req(payload_repeat_text, citation=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Citation matches \'name\''
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_text_admin_private
        res, project = req(payload_repeat_text, public=False, citation=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Citation matches \'name\''
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_text_non_admin_public
        res, project = req(payload_repeat_text, citation=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_text_non_admin_private
        res, project = req(payload_repeat_text, public=False, citation=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_text_non_contrib_public
        res, project = req(payload_repeat_text, citation=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_text_non_contrib_private
        res, project = req(payload_repeat_text, public=False, citation=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_text_logged_out_public
        res, project = req(payload_repeat_text, citation=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_add_repeat_text_logged_out_private
        res, project = req(payload_repeat_text, public=False, citation=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    def test_add_no_name_errors(self, req, payload_no_name):

    #   test_add_no_name_admin_public
        res, project = req(payload_no_name, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_name_admin_private
        res, project = req(payload_no_name, public=False, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_name_non_admin_public
        res, project = req(payload_no_name, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_name_non_admin_private
        res, project = req(payload_no_name, public=False, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_name_non_contrib_public
        res, project = req(payload_no_name, is_contrib=False, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_name_non_contrib_private
        res, project = req(payload_no_name, public=False, is_contrib=False, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_name_logged_out_public
        res, project = req(payload_no_name, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_name_logged_out_private
        res, project = req(payload_no_name, public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    def test_add_no_text_errors(self, req, payload_no_text):

    #   test_add_no_text_admin_public
        res, project = req(payload_no_text, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_text_admin_private
        res, project = req(payload_no_text, public=False, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_text_non_admin_public
        res, project = req(payload_no_text, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_text_non_admin_private
        res, project = req(payload_no_text, public=False, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_text_non_contrib_public
        res, project = req(payload_no_text, is_contrib=False, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_text_non_contrib_private
        res, project = req(payload_no_text, public=False, is_contrib=False, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_text_logged_out_public
        res, project = req(payload_no_text, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_no_text_logged_out_private
        res, project = req(payload_no_text, public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    def test_add_empty_errors(self, req, payload_empty):

    #   test_add_empty_admin_public
        res, project = req(payload_empty, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        assert res.json['errors'][0]['detail'] == res.json['errors'][1]['detail'], 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_empty_admin_private
        res, project = req(payload_empty, public=False, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        assert res.json['errors'][0]['detail'] == res.json['errors'][1]['detail'], 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_empty_non_admin_public
        res, project = req(payload_empty, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        assert res.json['errors'][0]['detail'] == res.json['errors'][1]['detail'], 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_empty_non_admin_private
        res, project = req(payload_empty, public=False, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        assert res.json['errors'][0]['detail'] == res.json['errors'][1]['detail'], 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_empty_non_contrib_public
        res, project = req(payload_empty, is_contrib=False, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        assert res.json['errors'][0]['detail'] == res.json['errors'][1]['detail'], 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_empty_non_contrib_private
        res, project = req(payload_empty, public=False, is_contrib=False, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        assert res.json['errors'][0]['detail'] == res.json['errors'][1]['detail'], 'This field is required.'
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_empty_logged_out_public
        res, project = req(payload_empty, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0

    #   test_add_empty_logged_out_private
        res, project = req(payload_empty, public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 0


@pytest.mark.django_db
class TestGetAlternativeCitations:

    @pytest.fixture()
    def req(self, app, create_project):
        def make_req(errors=False, is_admin=False, is_contrib=True, logged_out=False, **kwargs):
            admin = AuthUserFactory()
            registration = kwargs.get('registration', None)
            if is_admin:
                user = admin
            elif not logged_out:
                user = AuthUserFactory()
                kwargs['contrib'] = user if is_contrib else None
            project = create_project(admin, citation=True, **kwargs)
            if registration:
                project_url = '/{}registrations/{}/citations/'.format(API_BASE, project._id)
            else:
                project_url = '/{}nodes/{}/citations/'.format(API_BASE, project._id)
            if not logged_out:
                res = app.get(project_url, auth=user.auth, expect_errors=errors)
            else:
                res = app.get(project_url, expect_errors=errors)
            return res
        return make_req

    def test_get_alternative_citations(self, req):

    #   test_get_all_citations_admin_public
        res = req(is_admin=True)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_admin_private
        res = req(is_admin=True, public=False)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_non_admin_public
        res = req()
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_non_admin_private
        res = req(public=False)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_non_contrib_public
        res = req(is_contrib=False)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_non_contrib_private
        res = req(public=False, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_get_all_citations_logged_out_public
        res = req(logged_out=True)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_logged_out_private
        res = req(public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_get_all_citations_admin_public_reg
        res = req(registration=True, is_admin=True)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_admin_private_reg
        res = req(public=False, registration=True, is_admin=True)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_non_admin_public_reg
        res = req(registration=True)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_non_admin_private_reg
        res = req(public=False, registration=True)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_non_contrib_public_reg
        res = req(registration=True, is_contrib=False)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_non_contrib_private_reg
        res = req(public=False, registration=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_get_all_citations_logged_out_public_reg
        res = req(registration=True, logged_out=True)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['attributes']['text'] == 'text'
        assert data[0]['attributes']['name'] == 'name'

    #   test_get_all_citations_logged_out_private_reg
        res = req(public=False, registration=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
