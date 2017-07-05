import pytest

from api.base.settings.defaults import API_BASE
from api.citations import utils as citation_utils
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
    def make_payload(name=None, text=None, _id=None):
        data = {'data': {
            'type': 'citations',
            'attributes': {}
            }
        }
        if name is not None:
            data['data']['attributes']['name'] = name
        if text is not None:
            data['data']['attributes']['text'] = text
        if _id is not None:
            data['data']['id'] = _id
        return data
    return make_payload

@pytest.fixture()
def citation_and_project():
    def make_citation_and_project(admin, public=True, registration=False, contrib=None, citation2=False, for_delete=False, bad=False):
        project = ProjectFactory(creator=admin, is_public=public)
        citation = AlternativeCitationFactory(name='name', text='text')
        project.alternative_citations.add(citation)
        if contrib:
            project.add_contributor(contrib, permissions=[permissions.READ, permissions.WRITE], visible=True)
        if citation2:
            citation2 = AlternativeCitationFactory(name='name2', text='text2')
            project.alternative_citations.add(citation2)
        project.save()
        slug = 1 if bad else citation._id
        if registration:
            project = RegistrationFactory(project=project, is_public=public)
            citation_url = '/{}registrations/{}/citations/{}/'.format(API_BASE, project._id, slug)
        else:
            citation_url = '/{}nodes/{}/citations/{}/'.format(API_BASE, project._id, slug)
        if for_delete:
            return project, citation_url
        return citation, citation_url
    return make_citation_and_project

@pytest.mark.django_db
class TestUpdateAlternativeCitations:

    @pytest.fixture()
    def req(self, app, payload, citation_and_project):
        def make_req(is_admin=False, is_contrib=True, logged_out=False, errors=False, patch=False, **kwargs):
            name = kwargs.pop('name', None)
            text = kwargs.pop('text', None)
            admin = AuthUserFactory()
            if is_admin:
                user = admin
            elif not logged_out:
                user = AuthUserFactory()
                kwargs['contrib'] = user if is_contrib else None
            citation, citation_url = citation_and_project(admin, **kwargs)
            data = payload(name=name, text=text, _id=citation._id)
            if patch:
                if not logged_out:
                    res = app.patch_json_api(citation_url, data, auth=user.auth, expect_errors=errors)
                else:
                    res = app.patch_json_api(citation_url, data, expect_errors=errors)
            else:
                if not logged_out:
                    res = app.put_json_api(citation_url, data, auth=user.auth, expect_errors=errors)
                else:
                    res = app.put_json_api(citation_url, data, expect_errors=errors)
            return res, citation
        return make_req

    def test_update_citation_name_admin_public(self, req):
        res, citation = req(name='Test', text='text', is_admin=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'Test'
        citation.reload()
        assert citation.name == 'Test'

    def test_update_citation_name_admin_private(self, req):
        res, citation = req(name='Test', text='text', public=False, is_admin=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'Test'
        citation.reload()
        assert citation.name == 'Test'

    def test_update_citation_name_errors(self, req):

    #   test_update_citation_name_non_admin_public
        res, citation = req(name='Test', text='text', errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_name_non_admin_private
        res, citation = req(name='Test', text='text', public=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_name_non_contrib_public
        res, citation = req(name='Test', text='text', is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_name_non_contrib_private
        res, citation = req(name='Test', text='text', public=False, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_name_logged_out_public
        res, citation = req(name='Test', text='text', logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_name_logged_out_private
        res, citation = req(name='Test', text='text', public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.name == 'name'

    def test_update_citation_text_admin_public(self, req):
        res, citation = req(name='name', text='Test', is_admin=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['text'] == 'Test'
        citation.reload()
        assert citation.text == 'Test'

    def test_update_citation_text_admin_private(self, req):
        res, citation = req(name='name', text='Test', public=False, is_admin=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['text'] == 'Test'
        citation.reload()
        assert citation.text == 'Test'

    def test_update_citation_text_errors(self, req):

    #   test_update_citation_text_non_admin_public
        res, citation = req(name='name', text='Test', errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_text_non_admin_private
        res, citation = req(name='name', text='Test', public=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_text_non_contrib_public
        res, citation = req(name='name', text='Test', is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_text_non_contrib_private
        res, citation = req(name='name', text='Test', public=False,is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_text_logged_out_public
        res, citation = req(name='name', text='Test', logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_text_logged_out_private
        res, citation = req(name='name', text='Test', public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'

    def test_update_citation_admin_public(self, req):
        res, citation = req(name='Test', text='Test', is_admin=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == res.json['data']['attributes']['text'], 'Test'
        citation.reload()
        assert citation.name == citation.text, 'Test'

    def test_update_citation_admin_private(self, req):
        res, citation = req(name='Test', text='Test', public=False, is_admin=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == res.json['data']['attributes']['text'], 'Test'
        citation.reload()
        assert citation.name == citation.text, 'Test'

    def test_update_citation_errors(self, req):

    #   test_update_citation_non_admin_public
        res, citation = req(name='Test', text='Test', errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_non_admin_private
        res, citation = req(name='Test', text='Test', public=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_non_contrib_public
        res, citation = req(name='Test', text='Test', is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_non_contrib_private
        res, citation = req(name='Test', text='Test', public=False, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_logged_out_public
        res, citation = req(name='Test', text='Test', logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_logged_out_private
        res, citation = req(name='Test', text='Test', public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.name == 'name'
        assert citation.text == 'text'

    def test_update_citation_repeat_name_errors(self, req):

    #   test_update_citation_repeat_name_admin_public
        res, citation = req(name='name2', text='text', is_admin=True, citation2=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'There is already a citation named \'name2\''
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_repeat_name_admin_private
        res, citation = req(name='name2', text='text', public=False, is_admin=True, citation2=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'There is already a citation named \'name2\''
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_repeat_name_non_admin_public
        res, citation = req(name='name2', text='text', citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_repeat_name_non_admin_private
        res, citation = req(name='name2', text='text', public=False, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_repeat_name_non_contrib_public
        res, citation = req(name='name2', text='text', is_contrib=False, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_repeat_name_non_contrib_private
        res, citation = req(name='name2', text='text', public=False, is_contrib=False, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_repeat_name_logged_out_public
        res, citation = req(name='name2', text='text', logged_out=True, citation2=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.name == 'name'

    #   test_update_citation_repeat_name_logged_out_private
        res, citation = req(name='name2', text='text', public=False, logged_out=True, citation2=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.name == 'name'

    def test_update_repeat_text_errors(self, req):

    #   test_update_citation_repeat_text_admin_public
        res, citation = req(name='name', text='text2', is_admin=True, citation2=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Citation matches \'name2\''
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_repeat_text_admin_private
        res, citation = req(name='name', text='text2', public=False, is_admin=True, citation2=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Citation matches \'name2\''
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_repeat_text_non_admin_public
        res, citation = req(name='name', text='text2', citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_repeat_text_non_admin_private
        res, citation = req(name='name', text='text2', public=False, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_repeat_text_non_contrib_public
        res, citation = req(name='name', text='text2', is_contrib=False, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_repeat_text_non_contrib_private
        res, citation = req(name='name', text='text2', public=False, is_contrib=False, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_repeat_text_logged_out_public
        res, citation = req(name='name', text='text2', logged_out=True, citation2=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'

    #   test_update_citation_repeat_text_logged_out_private
        res, citation = req(name='name', text='text2', public=False, logged_out=True, citation2=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'

    def test_update_citation_repeat_errors(self, req):

    #   test_update_citation_repeat_admin_public
        res, citation = req(name='name2', text='text2', is_admin=True, citation2=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        errors = [error['detail'] for error in res.json['errors']]
        assert 'There is already a citation named \'name2\'' in errors
        assert 'Citation matches \'name2\'' in errors
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_repeat_admin_private
        res, citation = req(name='name2', text='text2', public=False, is_admin=True, citation2=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 2
        errors = [error['detail'] for error in res.json['errors']]
        assert 'There is already a citation named \'name2\'' in errors
        assert 'Citation matches \'name2\'' in errors
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_repeat_non_admin_public
        res, citation = req(name='name2', text='text2', citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_repeat_non_admin_private
        res, citation = req(name='name2', text='text2', public=False, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_repeat_non_contrib_public
        res, citation = req(name='name2', text='text2', is_contrib=False, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_repeat_non_contrib_private
        res, citation = req(name='name2', text='text2', public=False, is_contrib=False, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_repeat_logged_out_public
        res, citation = req(name='name2', text='text2', logged_out=True, citation2=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_repeat_logged_out_private
        res, citation = req(name='name2', text='text2', public=False, logged_out=True, citation2=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    def test_update_citation_empty_admin_public(self, req):
        res, citation = req(is_admin=True, patch=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'name'
        assert res.json['data']['attributes']['text'] == 'text'
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    def test_update_citation_empty_admin_private(self, req):
        res, citation = req(public=False, is_admin=True, patch=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'name'
        assert res.json['data']['attributes']['text'] == 'text'
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    def test_update_citation_empty_errors(self, req):

    #   test_update_citation_empty_non_admin_public
        res, citation = req(patch=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_empty_non_admin_private
        res, citation = req(public=False, patch=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_empty_non_contrib_public
        res, citation = req(is_contrib=False, patch=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_empty_non_contrib_private
        res, citation = req(public=False, is_contrib=False, patch=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_empty_logged_out_public
        res, citation = req(logged_out=True, patch=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_empty_logged_out_private
        res, citation = req(public=False, logged_out=True, patch=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    def test_update_citation_name_only_admin_public(self, req):
        res, citation = req(name='new name', patch=True, is_admin=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'new name'
        assert res.json['data']['attributes']['text'] == 'text'
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'new name'

    def test_update_citation_name_only_admin_private(self, req):
        res, citation = req(name='new name', public=False, patch=True, is_admin=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'new name'
        assert res.json['data']['attributes']['text'] == 'text'
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'new name'

    def test_update_citation_name_only_errors(self, req):

    #   test_update_citation_name_only_non_admin_public
        res, citation = req(name='new name', patch=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_non_admin_private
        res, citation = req(name='new name', public=False, patch=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_non_contrib_public
        res, citation = req(name='new name', patch=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_non_contrib_private
        res, citation = req(name='new name', public=False, patch=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_logged_out_public
        res, citation = req(name='new name', patch=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_logged_out_private
        res, citation = req(name='new name', public=False, patch=True,logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    def test_update_citation_text_only_admin_public(self, req):
        res, citation = req(text='new text', patch=True, is_admin=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == 'name'
        assert res.json['data']['attributes']['text'] == 'new text'
        citation.reload()
        assert citation.text == 'new text'
        assert citation.name == 'name'

    def test_update_citation_text_only_admin_private(self, req):
        res, citation = req(text='new text', public=False, patch=True, is_admin=True)
        assert res.status_code == 200
        citation.reload()
        assert res.json['data']['attributes']['name'] == 'name'
        assert res.json['data']['attributes']['text'] == 'new text'
        assert citation.text == 'new text'
        assert citation.name == 'name'

    def test_update_citation_text_only_errors(self, req):

    #   test_update_citation_text_only_non_admin_public
        res, citation = req(text='new text', patch=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_non_admin_private
        res, citation = req(text='new text', public=False, patch=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_non_contrib_public
        res, citation = req(text='new text', patch=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_non_contrib_private
        res, citation = req(text='new text', public=False, patch=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_logged_out_public
        res, citation = req(text='new text', patch=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_logged_out_private
        res, citation = req(text='new text', public=False, patch=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    def test_update_citation_name_only_repeat_errors(self, req):

    #   test_update_citation_name_only_repeat_admin_public
        res, citation = req(name='name2', patch=True, citation2=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'There is already a citation named \'name2\''
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_repeat_admin_private
        res, citation = req(name='name2', public=False, patch=True, citation2=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'There is already a citation named \'name2\''
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_repeat_non_admin_public
        res, citation = req(name='name2', patch=True, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_repeat_non_admin_private
        res, citation = req(name='name2', public=False, patch=True, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_repeat_non_contrib_public
        res, citation = req(name='name2', patch=True, citation2=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_repeat_non_contrib_private
        res, citation = req(name='name2', public=False, patch=True, citation2=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_repeat_logged_out_public
        res, citation = req(name='name2', patch=True, citation2=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_name_only_repeat_logged_out_private
        res, citation = req(name='name2', public=False, patch=True, citation2=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    def test_update_citation_text_only_repeat_errors(self, req):

    #   test_update_citation_text_only_repeat_admin_public
        res, citation = req(text='text2', patch=True, citation2=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Citation matches \'name2\''
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_repeat_admin_private
        res, citation = req(text='text2', public=False, patch=True, citation2=True, is_admin=True, errors=True)
        assert res.status_code == 400
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Citation matches \'name2\''
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_repeat_non_admin_public
        res, citation = req(text='text2', patch=True, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_repeat_non_admin_private
        res, citation = req(text='text2', public=False, patch=True, citation2=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_repeat_non_contrib_public
        res, citation = req(text='text2', patch=True, citation2=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_repeat_non_contrib_private
        res, citation = req(text='text2', public=False, patch=True, citation2=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_repeat_logged_out_public
        res, citation = req(text='text2', patch=True, citation2=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    #   test_update_citation_text_only_repeat_logged_out_private
        res, citation = req(text='text2', public=False, patch=True, citation2=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        citation.reload()
        assert citation.text == 'text'
        assert citation.name == 'name'

    def test_update_citation_errors(self, req):

    #   test_update_citation_admin_public_reg
        res, citation = req(name='test', text='Citation', registration=True, is_admin=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_admin_private_reg
        res, citation = req(name='test', text='Citation', public=False, registration=True, is_admin=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_non_admin_public_reg
        res, citation = req(name='test', text='Citation', registration=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_non_admin_private_reg
        res, citation = req(name='test', text='Citation', public=False, registration=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_non_contrib_public_reg
        res, citation = req(name='test', text='Citation', registration=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_non_contrib_private_reg
        res, citation = req(name='test', text='Citation', public=False, registration=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_logged_out_public_reg
        res, citation = req(name='test', text='Citation', registration=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        assert citation.name == 'name'
        assert citation.text == 'text'

    #   test_update_citation_logged_out_private_reg
        res, citation = req(name='test', text='Citation', public=False, registration=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        assert citation.name == 'name'
        assert citation.text == 'text'


@pytest.mark.django_db
class TestDeleteAlternativeCitations:

    @pytest.fixture()
    def req(self, app, citation_and_project):
        def make_request(is_admin=False, is_contrib=True, logged_out=False, errors=False, **kwargs):
            admin = AuthUserFactory()
            if is_admin:
                user = admin
            elif not logged_out:
                user = AuthUserFactory()
                kwargs['contrib'] = user if is_contrib else None
            project, citation_url = citation_and_project(admin, for_delete=True, **kwargs)
            if not logged_out:
                res = app.delete_json_api(citation_url, auth=user.auth, expect_errors=errors)
            else:
                res = app.delete_json_api(citation_url, expect_errors=errors)
            return res, project
        return make_request

    def test_delete_citation_admin_public(self, req):
        res, project = req(is_admin=True)
        assert res.status_code == 204
        project.reload()
        assert project.alternative_citations.count() == 0

    def test_delete_citation_admin_private(self, req):
        res, project = req(public=False, is_admin=True)
        assert res.status_code == 204
        project.reload()
        assert project.alternative_citations.count() == 0

    def test_delete_citation_errors(self, req):

    #   test_delete_citation_non_admin_public
        res, project = req(errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_non_admin_private
        res, project = req(public=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_non_contrib_public
        res, project = req(is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_non_contrib_private
        res, project = req(public=False, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_logged_out_public
        res, project = req(logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_logged_out_private
        res, project = req(public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_admin_not_found_public
        res, project = req(is_admin=True, bad=True, errors=True)
        assert res.status_code == 404
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Not found.'
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_admin_not_found_private
        res, project = req(public=False, is_admin=True, bad=True, errors=True)
        assert res.status_code == 404
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Not found.'
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_non_admin_not_found_public
        res, project = req(bad=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_non_admin_not_found_private
        res, project = req(public=False, bad=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_non_contrib_not_found_public
        res, project = req(is_contrib=False, bad=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_non_contrib_not_found_private
        res, project = req(public=False, is_contrib=False, bad=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_logged_out_not_found_public
        res, project = req(logged_out=True, bad=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_logged_out_not_found_private
        res, project = req(public=False, logged_out=True, bad=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        project.reload()
        assert project.alternative_citations.count() == 1

    #   test_delete_citation_admin_public_reg
        res, registration = req(registration=True, is_admin=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 1

    #   test_delete_citation_admin_private_reg
        res, registration = req(public=False, registration=True, is_admin=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 1

    #   test_delete_citation_non_admin_public_reg
        res, registration = req(registration=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 1

    #   test_delete_citation_non_admin_private_reg
        res, registration = req(public=False, registration=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 1

    #   test_delete_citation_non_contrib_public_reg
        res, registration = req(registration=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 1

    #   test_delete_citation_non_contrib_private_reg
        res, registration = req(public=False, registration=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail
        assert registration.alternative_citations.count() == 1

    #   test_delete_citation_logged_out_public_reg
        res, registration = req(registration=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        assert registration.alternative_citations.count() == 1

    #   test_delete_citation_logged_out_private_reg
        res, registration = req(public=False, registration=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail
        assert registration.alternative_citations.count() == 1


@pytest.mark.django_db
class TestGetAlternativeCitations:

    @pytest.fixture()
    def req(self, app, citation_and_project):
        def make_req(is_admin=False, is_contrib=True, logged_out=False, errors=False, **kwargs):
            admin = AuthUserFactory()
            if is_admin:
                user = admin
            elif not logged_out:
                user = AuthUserFactory()
                kwargs['contrib'] = user if is_contrib else None
            citation, citation_url = citation_and_project(admin, **kwargs)
            if not logged_out:
                res = app.get(citation_url, auth=user.auth, expect_errors=errors)
            else:
                res = app.get(citation_url, expect_errors=errors)
            return res, citation
        return make_req

    def test_get_citation(self, req):

    #   test_get_citation_admin_public
        res, citation = req(is_admin=True)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_admin_private
        res, citation = req(public=False,
                                     is_admin=True)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_non_admin_public
        res, citation = req()
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_non_admin_private
        res, citation = req(public=False)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_non_contrib_public
        res, citation = req(is_contrib=False)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_logged_out_public
        res, citation = req(logged_out=True)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_admin_public_reg
        res, citation = req(registration=True, is_admin=True)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_admin_private_reg
        res, citation = req(public=False, registration=True, is_admin=True)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_non_admin_public_reg
        res, citation = req(registration=True)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_non_admin_private_reg
        res, citation = req(public=False, registration=True)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_non_contrib_public_reg
        res, citation = req(registration=True, is_contrib=False)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    #   test_get_citation_logged_out_public_reg
        res, citation = req(registration=True, logged_out=True)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']
        assert attributes['name'] == 'name'
        assert attributes['text'] == 'text'

    def test_get_citation_errors(self, req):

    #   test_get_citation_non_contrib_private
        res, citation = req(public=False, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_get_citation_logged_out_private
        res, citation = req(public=False, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_get_citation_admin_not_found_public
        res, citation = req(is_admin=True, bad=True, errors=True)
        assert res.status_code == 404
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Not found.'

    #   test_get_citation_admin_not_found_private
        res, citation = req(public=False, is_admin=True, bad=True, errors=True)
        assert res.status_code == 404
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Not found.'

    #   test_get_citation_non_admin_not_found_public
        res, citation = req(bad=True, errors=True)
        assert res.status_code == 404
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Not found.'

    #   test_get_citation_non_admin_not_found_private
        res, citation = req(public=False, bad=True, errors=True)
        assert res.status_code == 404
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Not found.'

    #   test_get_citation_non_contrib_not_found_public
        res, citation = req(is_contrib=False, bad=True, errors=True)
        assert res.status_code == 404
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Not found.'

    #   test_get_citation_non_contrib_not_found_private
        res, citation = req(public=False, is_contrib=False, bad=True, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_get_citation_logged_out_not_found_public
        res, citation = req(logged_out=True, bad=True, errors=True)
        assert res.status_code == 404
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == 'Not found.'

    #   test_get_citation_logged_out_not_found_private
        res, citation = req(public=False, logged_out=True, bad=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_get_citation_non_contrib_private_reg
        res, citation = req(public=False, registration=True, is_contrib=False, errors=True)
        assert res.status_code == 403
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_get_citation_logged_out_private_reg
        res, citation = req(public=False, registration=True, logged_out=True, errors=True)
        assert res.status_code == 401
        assert len(res.json['errors']) == 1
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail


@pytest.mark.django_db
class TestManualCitationCorrections:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user, is_public=True, title='My Project')

    def test_apa_citation(self, user, project,):
        citation = citation_utils.render_citation(project, 'apa')
        expected_citation = user.family_name + ', ' + user.given_name_initial + '. (' + \
                            project.date_created.strftime("%Y, %B %-d") + '). ' + project.title + \
                            '. Retrieved from ' + project.display_absolute_url
        assert citation == expected_citation

    def test_mla_citation(self, project):
        csl = project.csl
        citation = citation_utils.render_citation(project, 'modern-language-association')
        expected_citation = csl['author'][0]['family'] + ', ' + csl['author'][0]['given'] + '. ' + u"\u201c" + csl['title'] + u"\u201d" + '. ' +\
                            csl['publisher'] + ', ' + (project.date_created.strftime("%-d %b. %Y. Web.") if project.date_created.month not in [5,6,7] else project.date_created.strftime("%-d %B %Y. Web."))
        assert citation == expected_citation

    def test_chicago_citation(self, project):
        csl = project.csl
        citation = citation_utils.render_citation(project, 'chicago-author-date')
        expected_citation = csl['author'][0]['family'] + ', ' + csl['author'][0]['given'] + '. ' + str(csl['issued']['date-parts'][0][0]) + '. ' + u"\u201c" + csl['title'] + u"\u201d" + '. ' +  csl['publisher'] +'. ' + project.date_created.strftime("%B %-d") + '. ' + csl['URL'] + '.'
        assert citation == expected_citation
