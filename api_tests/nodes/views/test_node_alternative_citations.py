from nose.tools import *  # flake8: noqa

from website.util import permissions

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase

from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    AlternativeCitationFactory
)

def payload(name=None, text=None, _id=None):
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

def set_up_citation_and_project(admin, public=True, registration=False, contrib=None, citation2=False, for_delete=False, bad=False):
    project = ProjectFactory(creator=admin, is_public=public)
    citation = AlternativeCitationFactory(name='name', text='text')
    project.alternative_citations.append(citation)
    if contrib:
        project.add_contributor(contrib, permissions=[permissions.READ, permissions.WRITE], visible=True)
    if citation2:
        citation2 = AlternativeCitationFactory(name='name2', text='text2')
        project.alternative_citations.append(citation2)
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

class TestUpdateAlternativeCitations(ApiTestCase):
    def request(self, is_admin=False, is_contrib=True, logged_out=False, errors=False, patch=False, **kwargs):
        name = kwargs.pop('name', None)
        text = kwargs.pop('text', None)
        admin = AuthUserFactory()
        if is_admin:
            user = admin
        elif not logged_out:
            user = AuthUserFactory()
            kwargs['contrib'] = user if is_contrib else None
        citation, citation_url = set_up_citation_and_project(admin, **kwargs)
        data = payload(name=name, text=text, _id=citation._id)
        if patch:
            if not logged_out:
                res = self.app.patch_json_api(citation_url, data, auth=user.auth, expect_errors=errors)
            else:
                res = self.app.patch_json_api(citation_url, data, expect_errors=errors)
        else:
            if not logged_out:
                res = self.app.put_json_api(citation_url, data, auth=user.auth, expect_errors=errors)
            else:
                res = self.app.put_json_api(citation_url, data, expect_errors=errors)
        return res, citation

    def test_update_citation_name_admin_public(self):
        res, citation = self.request(name="Test",
                                     text="text",
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'Test')
        citation.reload()
        assert_equal(citation.name, "Test")

    def test_update_citation_name_admin_private(self):
        res, citation = self.request(name="Test",
                                     text="text",
                                     public=False,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'Test')
        citation.reload()
        assert_equal(citation.name, "Test")

    def test_update_citation_name_non_admin_public(self):
        res, citation = self.request(name="Test",
                                     text="text",
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_non_admin_private(self):
        res, citation = self.request(name="Test",
                                     text="text",
                                     public=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_non_contrib_public(self):
        res, citation = self.request(name="Test",
                                     text="text",
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_non_contrib_private(self):
        res, citation = self.request(name="Test",
                                     text="text",
                                     public=False,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_logged_out_public(self):
        res, citation = self.request(name="Test",
                                     text="text",
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_logged_out_private(self):
        res, citation = self.request(name="Test",
                                     text="text",
                                     public=False,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_text_admin_public(self):
        res, citation = self.request(name="name",
                                     text="Test",
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['text'], 'Test')
        citation.reload()
        assert_equal(citation.text, "Test")

    def test_update_citation_text_admin_private(self):
        res, citation = self.request(name="name",
                                     text="Test",
                                     public=False,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['text'], 'Test')
        citation.reload()
        assert_equal(citation.text, "Test")

    def test_update_citation_text_non_admin_public(self):
        res, citation = self.request(name="name",
                                     text="Test",
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_non_admin_private(self):
        res, citation = self.request(name="name",
                                     text="Test",
                                     public=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_non_contrib_public(self):
        res, citation = self.request(name="name",
                                     text="Test",
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_non_contrib_private(self):
        res, citation = self.request(name="name",
                                     text="Test",
                                     public=False,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_logged_out_public(self):
        res, citation = self.request(name="name",
                                     text="Test",
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_logged_out_private(self):
        res, citation = self.request(name="name",
                                     text="Test",
                                     public=False,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_admin_public(self):
        res, citation = self.request(name="Test",
                                     text="Test",
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], res.json['data']['attributes']['text'], 'Test')
        citation.reload()
        assert_equal(citation.name, citation.text, "Test")

    def test_update_citation_admin_private(self):
        res, citation = self.request(name="Test",
                                     text="Test",
                                     public=False,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], res.json['data']['attributes']['text'], 'Test')
        citation.reload()
        assert_equal(citation.name, citation.text, "Test")

    def test_update_citation_non_admin_public(self):
        res, citation = self.request(name="Test",
                                     text="Test",
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_admin_private(self):
        res, citation = self.request(name="Test",
                                     text="Test",
                                     public=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_contrib_public(self):
        res, citation = self.request(name="Test",
                                     text="Test",
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_contrib_private(self):
        res, citation = self.request(name="Test",
                                     text="Test",
                                     public=False,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_logged_out_public(self):
        res, citation = self.request(name="Test",
                                     text="Test",
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_logged_out_private(self):
        res, citation = self.request(name="Test",
                                     text="Test",
                                     public=False,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_name_admin_public(self):
        res, citation = self.request(name="name2",
                                     text="text",
                                     is_admin=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already a citation named 'name2'")
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_admin_private(self):
        res, citation = self.request(name="name2",
                                     text="text",
                                     public=False,
                                     is_admin=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already a citation named 'name2'")
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_non_admin_public(self):
        res, citation = self.request(name="name2",
                                     text="text",
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_non_admin_private(self):
        res, citation = self.request(name="name2",
                                     text="text",
                                     public=False,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_non_contrib_public(self):
        res, citation = self.request(name="name2",
                                     text="text",
                                     is_contrib=False,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_non_contrib_private(self):
        res, citation = self.request(name="name2",
                                     text="text",
                                     public=False,
                                     is_contrib=False,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_logged_out_public(self):
        res, citation = self.request(name="name2",
                                     text="text",
                                     logged_out=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_logged_out_private(self):
        res, citation = self.request(name="name2",
                                     text="text",
                                     public=False,
                                     logged_out=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_text_admin_public(self):
        res, citation = self.request(name="name",
                                     text="text2",
                                     is_admin=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_admin_private(self):
        res, citation = self.request(name="name",
                                     text="text2",
                                     public=False,
                                     is_admin=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_non_admin_public(self):
        res, citation = self.request(name="name",
                                     text="text2",
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_non_admin_private(self):
        res, citation = self.request(name="name",
                                     text="text2",
                                     public=False,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_non_contrib_public(self):
        res, citation = self.request(name="name",
                                     text="text2",
                                     is_contrib=False,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_non_contrib_private(self):
        res, citation = self.request(name="name",
                                     text="text2",
                                     public=False,
                                     is_contrib=False,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_logged_out_public(self):
        res, citation = self.request(name="name",
                                     text="text2",
                                     logged_out=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_logged_out_private(self):
        res, citation = self.request(name="name",
                                     text="text2",
                                     public=False,
                                     logged_out=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_admin_public(self):
        res, citation = self.request(name="name2",
                                     text="text2",
                                     is_admin=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = [error['detail'] for error in res.json['errors']]
        assert_in("There is already a citation named 'name2'", errors)
        assert_in("Citation matches 'name2'", errors)
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_admin_private(self):
        res, citation = self.request(name="name2",
                                     text="text2",
                                     public=False,
                                     is_admin=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = [error['detail'] for error in res.json['errors']]
        assert_in("There is already a citation named 'name2'", errors)
        assert_in("Citation matches 'name2'", errors)
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_non_admin_public(self):
        res, citation = self.request(name="name2",
                                     text="text2",
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_non_admin_private(self):
        res, citation = self.request(name="name2",
                                     text="text2",
                                     public=False,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_non_contrib_public(self):
        res, citation = self.request(name="name2",
                                     text="text2",
                                     is_contrib=False,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_non_contrib_private(self):
        res, citation = self.request(name="name2",
                                     text="text2",
                                     public=False,
                                     is_contrib=False,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_logged_out_public(self):
        res, citation = self.request(name="name2",
                                     text="text2",
                                     logged_out=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_logged_out_private(self):
        res, citation = self.request(name="name2",
                                     text="text2",
                                     public=False,
                                     logged_out=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_admin_public(self):
        res, citation = self.request(is_admin=True,
                                     patch=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'name')
        assert_equal(res.json['data']['attributes']['text'], 'text')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_admin_private(self):
        res, citation = self.request(public=False,
                                     is_admin=True,
                                     patch=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'name')
        assert_equal(res.json['data']['attributes']['text'], 'text')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_non_admin_public(self):
        res, citation = self.request(patch=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_non_admin_private(self):
        res, citation = self.request(public=False,
                                     patch=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_non_contrib_public(self):
        res, citation = self.request(is_contrib=False,
                                     patch=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_non_contrib_private(self):
        res, citation = self.request(public=False,
                                     is_contrib=False,
                                     patch=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_logged_out_public(self):
        res, citation = self.request(logged_out=True,
                                     patch=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_logged_out_private(self):
        res, citation = self.request(public=False,
                                     logged_out=True,
                                     patch=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_admin_public(self):
        res, citation = self.request(name="new name",
                                     patch=True,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'new name')
        assert_equal(res.json['data']['attributes']['text'], 'text')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "new name")

    def test_update_citation_name_only_admin_private(self):
        res, citation = self.request(name="new name",
                                     public=False,
                                     patch=True,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'new name')
        assert_equal(res.json['data']['attributes']['text'], 'text')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "new name")

    def test_update_citation_name_only_non_admin_public(self):
        res, citation = self.request(name="new name",
                                     patch=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_non_admin_private(self):
        res, citation = self.request(name="new name",
                                     public=False,
                                     patch=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_non_contrib_public(self):
        res, citation = self.request(name="new name",
                                     patch=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_non_contrib_private(self):
        res, citation = self.request(name="new name",
                                     public=False,
                                     patch=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_logged_out_public(self):
        res, citation = self.request(name="new name",
                                     patch=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_logged_out_private(self):
        res, citation = self.request(name="new name",
                                     public=False,
                                     patch=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_admin_public(self):
        res, citation = self.request(text="new text",
                                     patch=True,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'name')
        assert_equal(res.json['data']['attributes']['text'], 'new text')
        citation.reload()
        assert_equal(citation.text, "new text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_admin_private(self):
        res, citation = self.request(text="new text",
                                     public=False,
                                     patch=True,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        citation.reload()
        assert_equal(res.json['data']['attributes']['name'], 'name')
        assert_equal(res.json['data']['attributes']['text'], 'new text')
        assert_equal(citation.text, "new text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_non_admin_public(self):
        res, citation = self.request(text="new text",
                                     patch=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_non_admin_private(self):
        res, citation = self.request(text="new text",
                                     public=False,
                                     patch=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_non_contrib_public(self):
        res, citation = self.request(text="new text",
                                     patch=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_non_contrib_private(self):
        res, citation = self.request(text="new text",
                                     public=False,
                                     patch=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_logged_out_public(self):
        res, citation = self.request(text="new text",
                                     patch=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_logged_out_private(self):
        res, citation = self.request(text="new text",
                                     public=False,
                                     patch=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_admin_public(self):
        res, citation = self.request(name="name2",
                                     patch=True,
                                     citation2=True,
                                     is_admin=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already a citation named 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_admin_private(self):
        res, citation = self.request(name="name2",
                                     public=False,
                                     patch=True,
                                     citation2=True,
                                     is_admin=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already a citation named 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_non_admin_public(self):
        res, citation = self.request(name="name2",
                                     patch=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_non_admin_private(self):
        res, citation = self.request(name="name2",
                                     public=False,
                                     patch=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_non_contrib_public(self):
        res, citation = self.request(name="name2",
                                     patch=True,
                                     citation2=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_non_contrib_private(self):
        res, citation = self.request(name="name2",
                                     public=False,
                                     patch=True,
                                     citation2=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_logged_out_public(self):
        res, citation = self.request(name="name2",
                                     patch=True,
                                     citation2=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_logged_out_private(self):
        res, citation = self.request(name="name2",
                                     public=False,
                                     patch=True,
                                     citation2=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_admin_public(self):
        res, citation = self.request(text="text2",
                                     patch=True,
                                     citation2=True,
                                     is_admin=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_admin_private(self):
        res, citation = self.request(text="text2",
                                     public=False,
                                     patch=True,
                                     citation2=True,
                                     is_admin=True,
                                     errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_non_admin_public(self):
        res, citation = self.request(text="text2",
                                     patch=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_non_admin_private(self):
        res, citation = self.request(text="text2",
                                     public=False,
                                     patch=True,
                                     citation2=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_non_contrib_public(self):
        res, citation = self.request(text="text2",
                                     patch=True,
                                     citation2=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_non_contrib_private(self):
        res, citation = self.request(text="text2",
                                     public=False,
                                     patch=True,
                                     citation2=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_logged_out_public(self):
        res, citation = self.request(text="text2",
                                     patch=True,
                                     citation2=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_logged_out_private(self):
        res, citation = self.request(text="text2",
                                     public=False,
                                     patch=True,
                                     citation2=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_admin_public_reg(self):
        res, citation = self.request(name="test",
                                     text="Citation",
                                     registration=True,
                                     is_admin=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_admin_private_reg(self):
        res, citation = self.request(name="test",
                                     text="Citation",
                                     public=False,
                                     registration=True,
                                     is_admin=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_admin_public_reg(self):
        res, citation = self.request(name="test",
                                     text="Citation",
                                     registration=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_admin_private_reg(self):
        res, citation = self.request(name="test",
                                     text="Citation",
                                     public=False,
                                     registration=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_contrib_public_reg(self):
        res, citation = self.request(name="test",
                                     text="Citation",
                                     registration=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_contrib_private_reg(self):
        res, citation = self.request(name="test",
                                     text="Citation",
                                     public=False,
                                     registration=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_logged_out_public_reg(self):
        res, citation = self.request(name="test",
                                     text="Citation",
                                     registration=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_logged_out_private_reg(self):
        res, citation = self.request(name="test",
                                     text="Citation",
                                     public=False,
                                     registration=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")


class TestDeleteAlternativeCitations(ApiTestCase):
    def request(self, is_admin=False, is_contrib=True, logged_out=False, errors=False, **kwargs):
        admin = AuthUserFactory()
        if is_admin:
            user = admin
        elif not logged_out:
            user = AuthUserFactory()
            kwargs['contrib'] = user if is_contrib else None
        project, citation_url = set_up_citation_and_project(admin, for_delete=True, **kwargs)
        if not logged_out:
            res = self.app.delete_json_api(citation_url, auth=user.auth, expect_errors=errors)
        else:
            res = self.app.delete_json_api(citation_url, expect_errors=errors)
        return res, project

    def test_delete_citation_admin_public(self):
        res, project = self.request(is_admin=True)
        assert_equal(res.status_code, 204)
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_delete_citation_admin_private(self):
        res, project = self.request(public=False,
                                    is_admin=True)
        assert_equal(res.status_code, 204)
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_delete_citation_non_admin_public(self):
        res, project = self.request(errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_non_admin_private(self):
        res, project = self.request(public=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_non_contrib_public(self):
        res, project = self.request(is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_non_contrib_private(self):
        res, project = self.request(public=False,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_logged_out_public(self):
        res, project = self.request(logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_logged_out_private(self):
        res, project = self.request(public=False,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_admin_not_found_public(self):
        res, project = self.request(is_admin=True,
                                    bad=True,
                                    errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_admin_not_found_private(self):
        res, project = self.request(public=False,
                                    is_admin=True,
                                    bad=True,
                                    errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_non_admin_not_found_public(self):
        res, project = self.request(bad=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_non_admin_not_found_private(self):
        res, project = self.request(public=False,
                                    bad=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_non_contrib_not_found_public(self):
        res, project = self.request(is_contrib=False,
                                    bad=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_non_contrib_not_found_private(self):
        res, project = self.request(public=False,
                                    is_contrib=False,
                                    bad=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_logged_out_not_found_public(self):
        res, project = self.request(logged_out=True,
                                    bad=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_logged_out_not_found_private(self):
        res, project = self.request(public=False,
                                    logged_out=True,
                                    bad=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_delete_citation_admin_public_reg(self):
        res, registration = self.request(registration=True,
                                         is_admin=True,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 1)

    def test_delete_citation_admin_private_reg(self):
        res, registration = self.request(public=False,
                                         registration=True,
                                         is_admin=True,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 1)

    def test_delete_citation_non_admin_public_reg(self):
        res, registration = self.request(registration=True,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 1)

    def test_delete_citation_non_admin_private_reg(self):
        res, registration = self.request(public=False,
                                         registration=True,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 1)

    def test_delete_citation_non_contrib_public_reg(self):
        res, registration = self.request(registration=True,
                                         is_contrib=False,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 1)

    def test_delete_citation_non_contrib_private_reg(self):
        res, registration = self.request(public=False,
                                         registration=True,
                                         is_contrib=False,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 1)

    def test_delete_citation_logged_out_public_reg(self):
        res, registration = self.request(registration=True,
                                         logged_out=True,
                                         errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(len(registration.alternative_citations), 1)

    def test_delete_citation_logged_out_private_reg(self):
        res, registration = self.request(public=False,
                                         registration=True,
                                         logged_out=True,
                                         errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(len(registration.alternative_citations), 1)

class TestGetAlternativeCitations(ApiTestCase):
    def request(self, is_admin=False, is_contrib=True, logged_out=False, errors=False, **kwargs):
        admin = AuthUserFactory()
        if is_admin:
            user = admin
        elif not logged_out:
            user = AuthUserFactory()
            kwargs['contrib'] = user if is_contrib else None
        citation, citation_url = set_up_citation_and_project(admin, **kwargs)
        if not logged_out:
            res = self.app.get(citation_url, auth=user.auth, expect_errors=errors)
        else:
            res = self.app.get(citation_url, expect_errors=errors)
        return res, citation

    def test_get_citation_admin_public(self):
        res, citation = self.request(is_admin=True)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_admin_private(self):
        res, citation = self.request(public=False,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_admin_public(self):
        res, citation = self.request()
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_admin_private(self):
        res, citation = self.request(public=False)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_contrib_public(self):
        res, citation = self.request(is_contrib=False)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_contrib_private(self):
        res, citation = self.request(public=False,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_citation_logged_out_public(self):
        res, citation = self.request(logged_out=True)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_logged_out_private(self):
        res, citation = self.request(public=False,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_get_citation_admin_not_found_public(self):
        res, citation = self.request(is_admin=True,
                                     bad=True,
                                     errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_admin_not_found_private(self):
        res, citation = self.request(public=False,
                                     is_admin=True,
                                     bad=True,
                                     errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_non_admin_not_found_public(self):
        res, citation = self.request(bad=True,
                                     errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_non_admin_not_found_private(self):
        res, citation = self.request(public=False,
                                     bad=True,
                                     errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_non_contrib_not_found_public(self):
        res, citation = self.request(is_contrib=False,
                                     bad=True,
                                     errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_non_contrib_not_found_private(self):
        res, citation = self.request(public=False,
                                     is_contrib=False,
                                     bad=True,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_citation_logged_out_not_found_public(self):
        res, citation = self.request(logged_out=True,
                                     bad=True,
                                     errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_logged_out_not_found_private(self):
        res, citation = self.request(public=False,
                                     logged_out=True,
                                     bad=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_get_citation_admin_public_reg(self):
        res, citation = self.request(registration=True,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_admin_private_reg(self):
        res, citation = self.request(public=False,
                                     registration=True,
                                     is_admin=True)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_admin_public_reg(self):
        res, citation = self.request(registration=True)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_admin_private_reg(self):
        res, citation = self.request(public=False,
                                     registration=True)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_contrib_public_reg(self):
        res, citation = self.request(registration=True,
                                     is_contrib=False)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_contrib_private_reg(self):
        res, citation = self.request(public=False,
                                     registration=True,
                                     is_contrib=False,
                                     errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_citation_logged_out_public_reg(self):
        res, citation = self.request(registration=True,
                                     logged_out=True)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_logged_out_private_reg(self):
        res, citation = self.request(public=False,
                                     registration=True,
                                     logged_out=True,
                                     errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
