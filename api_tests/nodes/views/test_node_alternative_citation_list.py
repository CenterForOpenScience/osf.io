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


def payload(name=None, text=None):
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


CITATION = payload(name='name', text='text')
REPEAT_NAME = payload(name='name', text='Citation')
REPEAT_TEXT = payload(name='Citation', text='text')
NO_NAME = payload(text='text')
NO_TEXT = payload(name='name')
EMPTY = payload()

def create_project(creator, public=True, contrib=None, citation=False, registration=False):
    project = ProjectFactory(creator=creator, is_public=public)
    if contrib:
        project.add_contributor(contrib, permissions=[permissions.READ, permissions.WRITE], visible=True)
    if citation:
        citation = AlternativeCitationFactory(name='name', text='text')
        project.alternative_citations.append(citation)
    project.save()
    if registration:
        registration = RegistrationFactory(project=project, is_public=public)
        return registration
    return project

class TestCreateAlternativeCitations(ApiTestCase):
    def request(self, data, errors=False, is_admin=False, is_contrib=True, logged_out=False, **kwargs):
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
            res = self.app.post_json_api(project_url, data, auth=user.auth, expect_errors=errors)
        else:
            res = self.app.post_json_api(project_url, data, expect_errors=errors)
        return res, project

    def test_add_citation_admin_public(self):
        res, project = self.request(CITATION, is_admin=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['name'], CITATION['data']['attributes']['name'])
        assert_equal(res.json['data']['attributes']['text'], CITATION['data']['attributes']['text'])
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_citation_admin_private(self):
        res, project = self.request(CITATION,
                                    is_admin=True,
                                    public=False)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['name'], CITATION['data']['attributes']['name'])
        assert_equal(res.json['data']['attributes']['text'], CITATION['data']['attributes']['text'])
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_citation_non_admin_public(self):
        res, project = self.request(CITATION,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_citation_non_admin_private(self):
        res, project = self.request(CITATION,
                                    public=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_citation_non_contrib_public(self):
        res, project = self.request(CITATION,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_citation_non_contrib_private(self):
        res, project = self.request(CITATION,
                                    public=False,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_citation_logged_out_public(self):
        res, project = self.request(CITATION,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_citation_logged_out_private(self):
        res, project = self.request(CITATION,
                                    public=False,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_repeat_name_admin_public(self):
        res, project = self.request(REPEAT_NAME,
                                    citation=True,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already a citation named 'name'")
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_admin_private(self):
        res, project = self.request(REPEAT_NAME,
                                    public=False,
                                    citation=True,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already a citation named 'name'")
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_non_admin_public(self):
        res, project = self.request(REPEAT_NAME,
                                    citation=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_non_admin_private(self):
        res, project = self.request(REPEAT_NAME,
                                    public=False,
                                    citation=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_non_contrib_public(self):
        res, project = self.request(REPEAT_NAME,
                                    citation=True,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_non_contrib_private(self):
        res, project = self.request(REPEAT_NAME,
                                    public=False,
                                    is_contrib=False,
                                    citation=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_logged_out_public(self):
        res, project = self.request(REPEAT_NAME,
                                    citation=True,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_logged_out_private(self):
        res, project = self.request(REPEAT_NAME,
                                    public=False,
                                    citation=True,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_text_admin_public(self):
        res, project = self.request(REPEAT_TEXT,
                                    citation=True,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name'")
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_text_admin_private(self):
        res, project = self.request(REPEAT_TEXT,
                                    public=False,
                                    citation=True,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name'")
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_text_non_admin_public(self):
        res, project = self.request(REPEAT_TEXT,
                                    citation=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_text_non_admin_private(self):
        res, project = self.request(REPEAT_TEXT,
                                    public=False,
                                    citation=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_text_non_contrib_public(self):
        res, project = self.request(REPEAT_TEXT,
                                    citation=True,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_text_non_contrib_private(self):
        res, project = self.request(REPEAT_TEXT,
                                    public=False,
                                    citation=True,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_text_logged_out_public(self):
        res, project = self.request(REPEAT_TEXT,
                                    citation=True,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_text_logged_out_private(self):
        res, project = self.request(REPEAT_TEXT,
                                    public=False,
                                    citation=True,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_and_text_admin_public(self):
        res, project = self.request(CITATION,
                                    citation=True,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = [error['detail'] for error in res.json['errors']]
        assert_in("There is already a citation named 'name'", errors)
        assert_in("Citation matches 'name'", errors)
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_and_text_admin_private(self):
        res, project = self.request(CITATION,
                                    public=False,
                                    citation=True,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = [error['detail'] for error in res.json['errors']]
        assert_in("There is already a citation named 'name'", errors)
        assert_in("Citation matches 'name'", errors)
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_and_text_non_admin_public(self):
        res, project = self.request(CITATION,
                                    citation=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_and_text_non_admin_private(self):
        res, project = self.request(CITATION,
                                    public=False,
                                    citation=True,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_and_text_non_contrib_public(self):
        res, project = self.request(CITATION,
                                    citation=True,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_and_text_non_contrib_private(self):
        res, project = self.request(CITATION,
                                    public=False,
                                    citation=True,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_and_text_logged_out_public(self):
        res, project = self.request(CITATION,
                                    citation=True,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_repeat_name_and_text_logged_out_private(self):
        res, project = self.request(CITATION,
                                    public=False,
                                    citation=True,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 1)

    def test_add_no_name_admin_public(self):
        res, project = self.request(NO_NAME,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_name_admin_private(self):
        res, project = self.request(NO_NAME,
                                    public=False,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_name_non_admin_public(self):
        res, project = self.request(NO_NAME,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_name_non_admin_private(self):
        res, project = self.request(NO_NAME,
                                    public=False,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_name_non_contrib_public(self):
        res, project = self.request(NO_NAME,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_name_non_contrib_private(self):
        res, project = self.request(NO_NAME,
                                    public=False,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_name_logged_out_public(self):
        res, project = self.request(NO_NAME,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_name_logged_out_private(self):
        res, project = self.request(NO_NAME,
                                    public=False,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_text_admin_public(self):
        res, project = self.request(NO_TEXT,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_text_admin_private(self):
        res, project = self.request(NO_TEXT,
                                    public=False,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_text_non_admin_public(self):
        res, project = self.request(NO_TEXT,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_text_non_admin_private(self):
        res, project = self.request(NO_TEXT,
                                    public=False,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_text_non_contrib_public(self):
        res, project = self.request(NO_TEXT,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_text_non_contrib_private(self):
        res, project = self.request(NO_TEXT,
                                    public=False,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_text_logged_out_public(self):
        res, project = self.request(NO_TEXT,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_no_text_logged_out_private(self):
        res, project = self.request(NO_TEXT,
                                    public=False,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_empty_admin_public(self):
        res, project = self.request(EMPTY,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_empty_admin_private(self):
        res, project = self.request(EMPTY,
                                    public=False,
                                    is_admin=True,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_empty_non_admin_public(self):
        res, project = self.request(EMPTY,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_empty_non_admin_private(self):
        res, project = self.request(EMPTY,
                                    public=False,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_empty_non_contrib_public(self):
        res, project = self.request(EMPTY,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_empty_non_contrib_private(self):
        res, project = self.request(EMPTY,
                                    public=False,
                                    is_contrib=False,
                                    errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_empty_logged_out_public(self):
        res, project = self.request(EMPTY,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)

    def test_add_empty_logged_out_private(self):
        res, project = self.request(EMPTY,
                                    public=False,
                                    logged_out=True,
                                    errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternative_citations), 0)
        
    def test_add_citation_admin_public_reg(self):
        res, registration = self.request(CITATION,
                                         registration=True,
                                         is_admin=True,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 0)

    def test_add_citation_admin_private_reg(self):
        res, registration = self.request(CITATION,
                                         public=False,
                                         registration=True,
                                         is_admin=True,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 0)

    def test_add_citation_non_admin_public_reg(self):
        res, registration = self.request(CITATION,
                                         registration=True,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 0)

    def test_add_citation_non_admin_private_reg(self):
        res, registration = self.request(CITATION,
                                         public=False,
                                         registration=True,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 0)

    def test_add_citation_non_contrib_public_reg(self):
        res, registration = self.request(CITATION,
                                         registration=True,
                                         is_contrib=False,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 0)

    def test_add_citation_non_contrib_private_reg(self):
        res, registration = self.request(CITATION,
                                         public=False,
                                         registration=True,
                                         is_contrib=False,
                                         errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(registration.alternative_citations), 0)

    def test_add_citation_logged_out_public_reg(self):
        res, registration = self.request(CITATION,
                                         registration=True,
                                         logged_out=True,
                                         errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(len(registration.alternative_citations), 0)

    def test_add_citation_logged_out_private_reg(self):
        res, registration = self.request(CITATION,
                                         public=False,
                                         registration=True,
                                         logged_out=True,
                                         errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(len(registration.alternative_citations), 0)


class TestGetAlternativeCitations(ApiTestCase):
    def request(self, errors=False, is_admin=False, is_contrib=True, logged_out=False, **kwargs):
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
            res = self.app.get(project_url, auth=user.auth, expect_errors=errors)
        else:
            res = self.app.get(project_url, expect_errors=errors)
        return res

    def test_get_all_citations_admin_public(self):
        res = self.request(is_admin=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_admin_private(self):
        res = self.request(is_admin=True,
                           public=False)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_non_admin_public(self):
        res = self.request()
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_non_admin_private(self):
        res = self.request(public=False)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_non_contrib_public(self):
        res = self.request(is_contrib=False)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_non_contrib_private(self):
        res = self.request(public=False,
                           is_contrib=False,
                           errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_all_citations_logged_out_public(self):
        res = self.request(logged_out=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_logged_out_private(self):
        res = self.request(public=False,
                           logged_out=True,
                           errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_get_all_citations_admin_public_reg(self):
        res = self.request(registration=True,
                           is_admin=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_admin_private_reg(self):
        res = self.request(public=False,
                           registration=True,
                           is_admin=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_non_admin_public_reg(self):
        res = self.request(registration=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_non_admin_private_reg(self):
        res = self.request(public=False,
                           registration=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_non_contrib_public_reg(self):
        res = self.request(registration=True,
                           is_contrib=False)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_non_contrib_private_reg(self):
        res = self.request(public=False,
                           registration=True,
                           is_contrib=False,
                           errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_all_citations_logged_out_public_reg(self):
        res = self.request(registration=True,
                           logged_out=True)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)
        assert_equal(data[0]['attributes']['text'], 'text')
        assert_equal(data[0]['attributes']['name'], 'name')

    def test_get_all_citations_logged_out_private_reg(self):
        res = self.request(public=False,
                           registration=True,
                           logged_out=True,
                           errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
