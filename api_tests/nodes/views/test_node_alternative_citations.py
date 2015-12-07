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


CITATION = payload(name='name', text='text')
REPEAT_NAME = payload(name='name', text='Citation')
REPEAT_TEXT = payload(name='Citation', text='text')
NO_NAME = payload(text='text')
NO_TEXT = payload(name='name')
EMPTY = payload()


class TestCreateAlternativeCitations(ApiTestCase):
    def project(self, creator, public=True, contributor=None, citation=None):
        project = ProjectFactory(creator=creator, is_public=public)
        project_url = '/{}nodes/{}/citations/'.format(API_BASE, project._id)
        if contributor:
            project.add_contributor(contributor, permissions=[permissions.READ, permissions.WRITE], visible=True)
        if citation:
            project.alternativeCitations.append(citation)
        project.save()
        return project, project_url

    def request(self, data, admin=False, contrib=True, logged_out=False, public=True, citation=False, errors=False):
        admin_user = AuthUserFactory()
        contrib_ = None
        user = None
        if not admin and not logged_out:
            user = AuthUserFactory()
            if contrib:
                contrib_ = user
        elif not logged_out:
            user = admin_user
        if citation:
            citation = AlternativeCitationFactory(name='name', text='text')
        project, project_url = self.project(admin_user, public=public, contributor=contrib_, citation=citation)
        if user:
            res = self.app.post_json_api(project_url, data, auth=user.auth, expect_errors=errors)
        else:
            res = self.app.post_json_api(project_url, data, expect_errors=errors)
        return res, project

    def test_add_citation_admin_public(self):
        res, project = self.request(CITATION, admin=True)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['name'], CITATION['data']['attributes']['name'])
        assert_equal(res.json['data']['attributes']['text'], CITATION['data']['attributes']['text'])
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_citation_admin_private(self):
        res, project = self.request(CITATION, admin=True, public=False)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['name'], CITATION['data']['attributes']['name'])
        assert_equal(res.json['data']['attributes']['text'], CITATION['data']['attributes']['text'])
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_citation_non_admin_public(self):
        res, project = self.request(CITATION, errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_citation_non_admin_private(self):
        res, project = self.request(CITATION, public=False, errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_citation_non_contrib_public(self):
        res, project = self.request(CITATION, contrib=False, errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_citation_non_contrib_private(self):
        res, project = self.request(CITATION, public=False, contrib=False, errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_citation_logged_out_public(self):
        res, project = self.request(CITATION, logged_out=True, errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_citation_logged_out_private(self):
        res, project = self.request(CITATION, public=False, logged_out=True, errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Authentication credentials were not provided.")
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_repeat_name_admin_public(self):
        data = dict()
        data['citation'] = True
        data['admin'] = True
        data['errors'] = True
        res, project = self.request(REPEAT_NAME, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name'")
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_admin_private(self):
        data = dict()
        data['citation'] = True
        data['admin'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(REPEAT_NAME, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name'")
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_non_admin_public(self):
        data = dict()
        data['citation'] = True
        data['errors'] = True
        res, project = self.request(REPEAT_NAME, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_non_admin_private(self):
        data = dict()
        data['citation'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(REPEAT_NAME, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_non_contrib_public(self):
        data = dict()
        data['citation'] = True
        data['contrib'] = False
        data['errors'] = True
        res, project = self.request(REPEAT_NAME, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_non_contrib_private(self):
        data = dict()
        data['citation'] = True
        data['contrib'] = False
        data['errors'] = True
        data['public'] = False
        res, project = self.request(REPEAT_NAME, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_logged_out_public(self):
        data = dict()
        data['citation'] = True
        data['logged_out'] = True
        data['errors'] = True
        res, project = self.request(REPEAT_NAME, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_logged_out_private(self):
        data = dict()
        data['citation'] = True
        data['logged_out'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(REPEAT_NAME, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_text_admin_public(self):
        data = dict()
        data['citation'] = True
        data['admin'] = True
        data['errors'] = True
        res, project = self.request(REPEAT_TEXT, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name'")
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_text_admin_private(self):
        data = dict()
        data['citation'] = True
        data['admin'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(REPEAT_TEXT, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name'")
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_text_non_admin_public(self):
        data = dict()
        data['citation'] = True
        data['errors'] = True
        res, project = self.request(REPEAT_TEXT, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_text_non_admin_private(self):
        data = dict()
        data['citation'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(REPEAT_TEXT, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_text_non_contrib_public(self):
        data = dict()
        data['citation'] = True
        data['contrib'] = False
        data['errors'] = True
        res, project = self.request(REPEAT_TEXT, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_text_non_contrib_private(self):
        data = dict()
        data['citation'] = True
        data['contrib'] = False
        data['errors'] = True
        data['public'] = False
        res, project = self.request(REPEAT_TEXT, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_text_logged_out_public(self):
        data = dict()
        data['citation'] = True
        data['logged_out'] = True
        data['errors'] = True
        res, project = self.request(REPEAT_TEXT, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_text_logged_out_private(self):
        data = dict()
        data['citation'] = True
        data['logged_out'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(REPEAT_TEXT, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_and_text_admin_public(self):
        data = dict()
        data['citation'] = True
        data['admin'] = True
        data['errors'] = True
        res, project = self.request(CITATION, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = [error['detail'] for error in res.json['errors']]
        assert_in("There is already an alternative citation named 'name'", errors)
        assert_in("Citation matches 'name'", errors)
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_and_text_admin_private(self):
        data = dict()
        data['citation'] = True
        data['admin'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(CITATION, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = [error['detail'] for error in res.json['errors']]
        assert_in("There is already an alternative citation named 'name'", errors)
        assert_in("Citation matches 'name'", errors)
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_and_text_non_admin_public(self):
        data = dict()
        data['citation'] = True
        data['errors'] = True
        res, project = self.request(CITATION, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_and_text_non_admin_private(self):
        data = dict()
        data['citation'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(CITATION, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_and_text_non_contrib_public(self):
        data = dict()
        data['citation'] = True
        data['contrib'] = False
        data['errors'] = True
        res, project = self.request(CITATION, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_and_text_non_contrib_private(self):
        data = dict()
        data['citation'] = True
        data['contrib'] = False
        data['errors'] = True
        data['public'] = False
        res, project = self.request(CITATION, **data)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_and_text_logged_out_public(self):
        data = dict()
        data['citation'] = True
        data['logged_out'] = True
        data['errors'] = True
        res, project = self.request(CITATION, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_repeat_name_and_text_logged_out_private(self):
        data = dict()
        data['citation'] = True
        data['logged_out'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(CITATION, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_add_no_name_admin_public(self):
        data = dict()
        data['admin'] = True
        data['errors'] = True
        res, project = self.request(NO_NAME, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_name_admin_private(self):
        data = dict()
        data['admin'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(NO_NAME, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_name_non_admin_public(self):
        data = dict()
        data['errors'] = True
        res, project = self.request(NO_NAME, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_name_non_admin_private(self):
        data = dict()
        data['errors'] = True
        data['public'] = False
        res, project = self.request(NO_NAME, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_name_non_contrib_public(self):
        data = dict()
        data['contrib'] = False
        data['errors'] = True
        res, project = self.request(NO_NAME, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_name_non_contrib_private(self):
        data = dict()
        data['contrib'] = False
        data['errors'] = True
        data['public'] = False
        res, project = self.request(NO_NAME, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_name_logged_out_public(self):
        data = dict()
        data['logged_out'] = True
        data['errors'] = True
        res, project = self.request(NO_NAME, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_name_logged_out_private(self):
        data = dict()
        data['logged_out'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(NO_NAME, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_text_admin_public(self):
        data = dict()
        data['admin'] = True
        data['errors'] = True
        res, project = self.request(NO_TEXT, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_text_admin_private(self):
        data = dict()
        data['admin'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(NO_TEXT, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_text_non_admin_public(self):
        data = dict()
        data['errors'] = True
        res, project = self.request(NO_TEXT, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_text_non_admin_private(self):
        data = dict()
        data['errors'] = True
        data['public'] = False
        res, project = self.request(NO_TEXT, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_text_non_contrib_public(self):
        data = dict()
        data['contrib'] = False
        data['errors'] = True
        res, project = self.request(NO_TEXT, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_text_non_contrib_private(self):
        data = dict()
        data['contrib'] = False
        data['errors'] = True
        data['public'] = False
        res, project = self.request(NO_TEXT, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_text_logged_out_public(self):
        data = dict()
        data['logged_out'] = True
        data['errors'] = True
        res, project = self.request(NO_TEXT, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_no_text_logged_out_private(self):
        data = dict()
        data['logged_out'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(NO_TEXT, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_empty_admin_public(self):
        data = dict()
        data['admin'] = True
        data['errors'] = True
        res, project = self.request(EMPTY, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_empty_admin_private(self):
        data = dict()
        data['admin'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(EMPTY, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_empty_non_admin_public(self):
        data = dict()
        data['errors'] = True
        res, project = self.request(EMPTY, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_empty_non_admin_private(self):
        data = dict()
        data['errors'] = True
        data['public'] = False
        res, project = self.request(EMPTY, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_empty_non_contrib_public(self):
        data = dict()
        data['contrib'] = False
        data['errors'] = True
        res, project = self.request(EMPTY, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_empty_non_contrib_private(self):
        data = dict()
        data['contrib'] = False
        data['errors'] = True
        data['public'] = False
        res, project = self.request(EMPTY, **data)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        assert_equal(res.json['errors'][0]['detail'], res.json['errors'][1]['detail'], 'This field is required.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_empty_logged_out_public(self):
        data = dict()
        data['logged_out'] = True
        data['errors'] = True
        res, project = self.request(EMPTY, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_add_empty_logged_out_private(self):
        data = dict()
        data['logged_out'] = True
        data['errors'] = True
        data['public'] = False
        res, project = self.request(EMPTY, **data)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

class TestUpdateAlternativeCitations(ApiTestCase):
    def setUp(self):
        super(TestUpdateAlternativeCitations, self).setUp()
        self.user = AuthUserFactory()

    def citation(self, name='name', text='text', public=True, contributor=None, citation2=None):
        project = ProjectFactory(creator=self.user, is_public=public)
        project_url = '/{}nodes/{}/citations/'.format(API_BASE, project._id)
        citation = AlternativeCitationFactory(name=name, text=text)
        project.alternativeCitations.append(citation)
        if contributor:
            project.add_contributor(contributor, permissions=[permissions.READ, permissions.WRITE], visible=True)
        if citation2:
            project.alternativeCitations.append(citation2)
        project.save()
        citation_url = project_url + '{}/'.format(citation._id)
        return citation, citation_url

    def test_update_citation_name_admin_public(self):
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="Test", text="text", _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'Test')
        citation.reload()
        assert_equal(citation.name, "Test")

    def test_update_citation_name_admin_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="text", _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'Test')
        citation.reload()
        assert_equal(citation.name, "Test")

    def test_update_citation_name_non_admin_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="text", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_non_admin_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False, contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="text", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_non_contrib_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="Test", text="text", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_non_contrib_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="text", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_logged_out_public(self):
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="Test", text="text", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_name_logged_out_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="text", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_text_admin_public(self):
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="name", text="Test", _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['text'], 'Test')
        citation.reload()
        assert_equal(citation.text, "Test")

    def test_update_citation_text_admin_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="name", text="Test", _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['text'], 'Test')
        citation.reload()
        assert_equal(citation.text, "Test")

    def test_update_citation_text_non_admin_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="name", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_non_admin_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False, contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="name", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_non_contrib_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="name", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_non_contrib_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="name", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_logged_out_public(self):
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="name", text="Test", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_text_logged_out_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="name", text="Test", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_admin_public(self):
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="Test", text="Test", _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], res.json['data']['attributes']['text'], 'Test')
        citation.reload()
        assert_equal(citation.name, citation.text, "Test")

    def test_update_citation_admin_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="Test", _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], res.json['data']['attributes']['text'], 'Test')
        citation.reload()
        assert_equal(citation.name, citation.text, "Test")

    def test_update_citation_non_admin_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_admin_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False, contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_contrib_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="Test", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_non_contrib_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_logged_out_public(self):
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="Test", text="Test", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_logged_out_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="Test", text="Test", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_name_admin_public(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(citation2=citation2)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="Test", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name2'")
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_admin_private(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, citation2=citation2)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="Test", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name2'")
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_non_admin_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_non_admin_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False, contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_non_contrib_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="name2", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_non_contrib_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="Test", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_logged_out_public(self):
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="name2", text="Test", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_name_logged_out_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="Test", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_text_admin_public(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(citation2=citation2)
        res = self.app.put_json_api(citation_url, payload(name="name", text="text2", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_admin_private(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, citation2=citation2)
        res = self.app.put_json_api(citation_url, payload(name="name", text="text2", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_non_admin_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="name", text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_non_admin_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user, public=False)
        res = self.app.put_json_api(citation_url, payload(name="name", text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_non_contrib_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="name", text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_non_contrib_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="name", text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_logged_out_public(self):
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="name", text="text2", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_text_logged_out_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="name", text="text2", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")

    def test_update_citation_repeat_admin_public(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(citation2=citation2)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="text2", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = [error['detail'] for error in res.json['errors']]
        assert_in("There is already an alternative citation named 'name2'", errors)
        assert_in("Citation matches 'name2'", errors)
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_admin_private(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, citation2=citation2)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="text2", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 2)
        errors = [error['detail'] for error in res.json['errors']]
        assert_in("There is already an alternative citation named 'name2'", errors)
        assert_in("Citation matches 'name2'", errors)
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_non_admin_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_non_admin_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False, contributor=user)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_non_contrib_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="name2", text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_non_contrib_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_logged_out_public(self):
        citation, citation_url = self.citation()
        res = self.app.put_json_api(citation_url, payload(name="name2", text="text2", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_repeat_logged_out_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.put_json_api(citation_url, payload(name="name2", text="text2", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_admin_public(self):
        citation, citation_url = self.citation()
        res = self.app.patch_json_api(citation_url, payload(_id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], 'name')
        assert_equal(res.json['data']['attributes']['text'], 'text')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_admin_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.patch_json_api(citation_url, payload(_id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_non_admin_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user)
        res = self.app.patch_json_api(citation_url, payload(_id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_non_admin_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False, contributor=user)
        res = self.app.patch_json_api(citation_url, payload(_id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_non_contrib_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation()
        res = self.app.patch_json_api(citation_url, payload(_id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_non_contrib_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False)
        res = self.app.patch_json_api(citation_url, payload(_id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_logged_out_public(self):
        citation, citation_url = self.citation()
        res = self.app.patch_json_api(citation_url, payload(_id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_empty_logged_out_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.patch_json_api(citation_url, payload(_id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_admin_public(self):
        citation, citation_url = self.citation()
        res = self.app.patch_json_api(citation_url, payload(name='new name', _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "new name")

    def test_update_citation_name_only_admin_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.patch_json_api(citation_url, payload(name='new name', _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "new name")

    def test_update_citation_name_only_non_admin_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user)
        res = self.app.patch_json_api(citation_url, payload(name='new name', _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_non_admin_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False, contributor=user)
        res = self.app.patch_json_api(citation_url, payload(name='new name', _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_non_contrib_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation()
        res = self.app.patch_json_api(citation_url, payload(name='new name', _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_non_contrib_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False)
        res = self.app.patch_json_api(citation_url, payload(name='new name', _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_logged_out_public(self):
        citation, citation_url = self.citation()
        res = self.app.patch_json_api(citation_url, payload(name='new name', _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_logged_out_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.patch_json_api(citation_url, payload(name='new name', _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_admin_public(self):
        citation, citation_url = self.citation()
        res = self.app.patch_json_api(citation_url, payload(text='new text', _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        citation.reload()
        assert_equal(citation.text, "new text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_admin_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.patch_json_api(citation_url, payload(text='new text', _id=citation._id), auth=self.user.auth)
        assert_equal(res.status_code, 200)
        citation.reload()
        assert_equal(citation.text, "new text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_non_admin_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(contributor=user)
        res = self.app.patch_json_api(citation_url, payload(text='new text', _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_non_admin_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False, contributor=user)
        res = self.app.patch_json_api(citation_url, payload(text='new text', _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_non_contrib_public(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation()
        res = self.app.patch_json_api(citation_url, payload(text='new text', _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_non_contrib_private(self):
        user = AuthUserFactory()
        citation, citation_url = self.citation(public=False)
        res = self.app.patch_json_api(citation_url, payload(text='new text', _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_logged_out_public(self):
        citation, citation_url = self.citation()
        res = self.app.patch_json_api(citation_url, payload(text='new text', _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_logged_out_private(self):
        citation, citation_url = self.citation(public=False)
        res = self.app.patch_json_api(citation_url, payload(text='new text', _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_admin_public(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(name="name2", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_admin_private(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(name="name2", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "There is already an alternative citation named 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_non_admin_public(self):
        user = AuthUserFactory()
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(contributor=user, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(name="name2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_non_admin_private(self):
        user = AuthUserFactory()
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, contributor=user, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(name="name2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_non_contrib_public(self):
        user = AuthUserFactory()
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(name="name2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_non_contrib_private(self):
        user = AuthUserFactory()
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(name="name2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_logged_out_public(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(name="name2", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_name_only_repeat_logged_out_private(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(name="name2", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_admin_public(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(text="text2", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_admin_private(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(text="text2", _id=citation._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], "Citation matches 'name2'")
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_non_admin_public(self):
        user = AuthUserFactory()
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(contributor=user, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_non_admin_private(self):
        user = AuthUserFactory()
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, contributor=user, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_non_contrib_public(self):
        user = AuthUserFactory()
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_non_contrib_private(self):
        user = AuthUserFactory()
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(text="text2", _id=citation._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_logged_out_public(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(text="text2", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")

    def test_update_citation_text_only_repeat_logged_out_private(self):
        citation2 = AlternativeCitationFactory(name="name2", text="text2")
        citation, citation_url = self.citation(public=False, citation2=citation2)
        res = self.app.patch_json_api(citation_url, payload(text="text2", _id=citation._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        citation.reload()
        assert_equal(citation.text, "text")
        assert_equal(citation.name, "name")


class TestDeleteAlternativeCitations(ApiTestCase):
    def setUp(self):
        super(TestDeleteAlternativeCitations, self).setUp()
        self.user = AuthUserFactory()
        self.citation = AlternativeCitationFactory(name="name", text="text")

    def project(self, public=True, contributor=None, bad=False):
        project = ProjectFactory(creator=self.user, is_public=public)
        project_url = '/{}nodes/{}/citations/'.format(API_BASE, project._id)
        if bad:
            project_url += '1/'
        if contributor:
            project.add_contributor(contributor, permissions=[permissions.READ, permissions.WRITE], visible=True)
        project.alternativeCitations.append(self.citation)
        citation_url = project_url + '{}/'.format(self.citation._id)
        project.save()
        return project, project_url, citation_url

    def test_delete_citation_admin_public(self):
        project, project_url, citation_url = self.project()
        res = self.app.delete_json_api(citation_url, auth=self.user.auth)
        assert_equal(res.status_code, 204)
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_delete_citation_admin_private(self):
        project, project_url, citation_url = self.project(public=False)
        res = self.app.delete_json_api(citation_url, auth=self.user.auth)
        assert_equal(res.status_code, 204)
        project.reload()
        assert_equal(len(project.alternativeCitations), 0)

    def test_delete_citation_non_admin_public(self):
        user = AuthUserFactory()
        project, project_url, citation_url = self.project(contributor=user)
        res = self.app.delete_json_api(citation_url, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_non_admin_private(self):
        user = AuthUserFactory()
        project, project_url, citation_url = self.project(public=False, contributor=user)
        res = self.app.delete_json_api(citation_url, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_non_contrib_public(self):
        user = AuthUserFactory()
        project, project_url, citation_url = self.project()
        res = self.app.delete_json_api(citation_url, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_non_contrib_private(self):
        user = AuthUserFactory()
        project, project_url, citation_url = self.project(public=False)
        res = self.app.delete_json_api(citation_url, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_logged_out_public(self):
        project, project_url, citation_url = self.project()
        res = self.app.delete_json_api(citation_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_logged_out_private(self):
        project, project_url, citation_url = self.project(public=False)
        res = self.app.delete_json_api(citation_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_admin_not_found_public(self):
        project, project_url_bad, citation_url = self.project(bad=True)
        res = self.app.delete_json_api(project_url_bad, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_admin_not_found_private(self):
        project, project_url_bad, citation_url = self.project(public=False, bad=True)
        res = self.app.delete_json_api(project_url_bad, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_non_admin_not_found_public(self):
        user = AuthUserFactory()
        project, project_url_bad, citation_url = self.project(contributor=user, bad=True)
        res = self.app.delete_json_api(project_url_bad, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_non_admin_not_found_private(self):
        user = AuthUserFactory()
        project, project_url_bad, citation_url = self.project(public=False, contributor=user, bad=True)
        res = self.app.delete_json_api(project_url_bad, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_non_contrib_not_found_public(self):
        user = AuthUserFactory()
        project, project_url_bad, citation_url = self.project(bad=True)
        res = self.app.delete_json_api(project_url_bad, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_non_contrib_not_found_private(self):
        user = AuthUserFactory()
        project, project_url_bad, citation_url = self.project(public=False, bad=True)
        res = self.app.delete_json_api(project_url_bad, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_logged_out_not_found_public(self):
        project, project_url_bad, citation_url = self.project(bad=True)
        res = self.app.delete_json_api(project_url_bad, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)

    def test_delete_citation_logged_out_not_found_private(self):
        project, project_url_bad, citation_url = self.project(bad=True)
        res = self.app.delete_json_api(project_url_bad, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        project.reload()
        assert_equal(len(project.alternativeCitations), 1)
#
class TestGetAlternativeCitations(ApiTestCase):
    def setUp(self):
        super(TestGetAlternativeCitations, self).setUp()
        self.user = AuthUserFactory()

    def create(self, public=True, contributor=None, citation=False, citation2=False, bad=False):
        data = dict()
        data['project'] = ProjectFactory(creator=self.user, is_public=public)
        data['project_url'] = '/{}nodes/{}/citations/'.format(API_BASE, data['project']._id)
        if citation:
            data['citation'] = AlternativeCitationFactory(name='name', text='text')
            data['project'].alternativeCitations.append(data['citation'])
            if not bad:
                data['citation_url'] = data['project_url'] + '{}/'.format(data['citation']._id)
            else:
                data['citation_url'] = data['project_url'] + '1/'
        if contributor:
            data['project'].add_contributor(contributor, permissions=[permissions.READ, permissions.WRITE], visible=True)
        if citation2:
            citation2 = AlternativeCitationFactory(name='name2', text='text2')
            data['project'].alternativeCitations.append(citation2)
        data['project'].save()
        return data

    def test_get_citation_admin_public(self):
        data = self.create(citation=True)
        res = self.app.get(data['citation_url'], auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_admin_private(self):
        data = self.create(public=False, citation=True)
        res = self.app.get(data['citation_url'], auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_admin_public(self):
        user = AuthUserFactory()
        data = self.create(contributor=user, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_admin_private(self):
        user = AuthUserFactory()
        data = self.create(public=False, contributor=user, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_contrib_public(self):
        user = AuthUserFactory()
        data = self.create(citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth, citation=True)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_non_contrib_private(self):
        user = AuthUserFactory()
        data = self.create(public=False, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_citation_logged_out_public(self):
        data = self.create(citation=True)
        res = self.app.get(data['citation_url'])
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_citation_logged_out_private(self):
        data = self.create(public=False, citation=True)
        res = self.app.get(data['citation_url'], expect_errors=True, )
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_get_citation_admin_not_found_public(self):
        data = self.create(bad=True, citation=True)
        res = self.app.get(data['citation_url'], auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_admin_not_found_private(self):
        data = self.create(public=False, bad=True, citation=True)
        res = self.app.get(data['citation_url'], auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_non_admin_not_found_public(self):
        user = AuthUserFactory()
        data = self.create(contributor=user, bad=True, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_non_admin_not_found_private(self):
        user = AuthUserFactory()
        data = self.create(public=False, contributor=user, bad=True, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_non_contrib_not_found_public(self):
        user = AuthUserFactory()
        data = self.create(bad=True, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_non_contrib_not_found_private(self):
        user = AuthUserFactory()
        data = self.create(public=False, bad=True, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_citation_logged_out_not_found_public(self):
        data = self.create(bad=True, citation=True)
        res = self.app.get(data['citation_url'], expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_get_citation_logged_out_not_found_private(self):
        data = self.create(public=False, bad=True, citation=True)
        res = self.app.get(data['citation_url'], expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_get_all_citations_admin_public(self):
        data = self.create(citation=True)
        res = self.app.get(data['project_url'], auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_citations_admin_private(self):
        data = self.create(public=False, citation=True)
        res = self.app.get(data['project_url'], auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_citations_non_admin_public(self):
        user = AuthUserFactory()
        data = self.create(contributor=user, citation=True)
        res = self.app.get(data['project_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_citations_non_admin_private(self):
        user = AuthUserFactory()
        data = self.create(public=False, contributor=user, citation=True)
        res = self.app.get(data['project_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_citations_non_contrib_public(self):
        user = AuthUserFactory()
        data = self.create(citation=True)
        res = self.app.get(data['project_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_citations_non_contrib_private(self):
        user = AuthUserFactory()
        data = self.create(public=False, citation=True)
        res = self.app.get(data['project_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_all_citations_logged_out_public(self):
        data = self.create(citation=True)
        res = self.app.get(data['project_url'])
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_citations_logged_out_private(self):
        data = self.create(public=False, citation=True)
        res = self.app.get(data['project_url'], expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

class TestRegistrationAlternativeCitations(ApiTestCase):
    def setUp(self):
        super(TestRegistrationAlternativeCitations, self).setUp()
        self.user = AuthUserFactory()

    def create(self, public=True, contributor=None, citation=False, bad=False):
        data = dict()
        data['project'] = ProjectFactory(creator=self.user)
        if citation:
            data['citation'] = AlternativeCitationFactory(name='name', text='text')
            data['project'].alternativeCitations.append(data['citation'])
        if contributor:
            data['project'].add_contributor(contributor, permissions=[permissions.READ, permissions.WRITE], visible=True)
        data['project'].save()
        data['registration'] = RegistrationFactory(project=data['project'], is_public=public)
        data['reg_url'] = '/{}nodes/{}/citations/'.format(API_BASE, data['registration']._id)
        if citation and not bad:
            data['citation_url'] = data['reg_url'] + '{}/'.format(data['citation']._id)
        elif citation:
            data['citation_url'] = data['reg_url'] + '1/'
        return data

    def test_get_all_public_reg_citations_admin(self):
        data = self.create(citation=True)
        res = self.app.get(data['reg_url'], auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_private_reg_citations_admin(self):
        data = self.create(public=False, citation=True)
        res = self.app.get(data['reg_url'], auth=self.user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_public_reg_citations_non_admin(self):
        user = AuthUserFactory()
        data = self.create(contributor=user, citation=True)
        res = self.app.get(data['reg_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_private_reg_citations_non_admin(self):
        user = AuthUserFactory()
        data = self.create(public=False, contributor=user, citation=True)
        res = self.app.get(data['reg_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_public_reg_citations_non_contrib(self):
        user = AuthUserFactory()
        data = self.create(citation=True)
        res = self.app.get(data['reg_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_private_reg_citations_non_contrib(self):
        user = AuthUserFactory()
        data = self.create(public=False, citation=True)
        res = self.app.get(data['reg_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_all_public_reg_citations_logged_out(self):
        data = self.create(citation=True)
        res = self.app.get(data['reg_url'])
        assert_equal(res.status_code, 200)
        data = res.json['data']
        assert_equal(len(data), 1)

    def test_get_all_private_reg_citations_logged_out(self):
        data = self.create(public=False, citation=True)
        res = self.app.get(data['reg_url'], expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_get_public_reg_citation_admin(self):
        data = self.create(citation=True)
        res = self.app.get(data['citation_url'], auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_private_reg_citation_admin(self):
        data = self.create(public=False, citation=True)
        res = self.app.get(data['citation_url'], auth=self.user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_public_reg_citation_non_admin(self):
        user = AuthUserFactory()
        data = self.create(contributor=user, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_private_reg_citation_non_admin(self):
        user = AuthUserFactory()
        data = self.create(public=False, contributor=user, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_public_reg_citation_non_contrib(self):
        user = AuthUserFactory()
        data = self.create(citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth)
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_private_reg_citation_non_contrib(self):
        user = AuthUserFactory()
        data = self.create(public=False, citation=True)
        res = self.app.get(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_get_public_reg_citation_logged_out(self):
        data = self.create(citation=True)
        res = self.app.get(data['citation_url'])
        assert_equal(res.status_code, 200)
        attributes = res.json['data']['attributes']
        assert_equal(attributes['name'], 'name')
        assert_equal(attributes['text'], 'text')

    def test_get_private_reg_citation_logged_out(self):
        data = self.create(public=False, citation=True)
        res = self.app.get(data['citation_url'], expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_create_public_reg_citation_admin(self):
        data = self.create()
        res = self.app.post_json_api(data['reg_url'], payload(name="test", text='Citation'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 0)

    def test_create_private_reg_citation_admin(self):
        data = self.create(public=False)
        res = self.app.post_json_api(data['reg_url'], payload(name="test", text='Citation'), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 0)

    def test_create_public_reg_citation_non_admin(self):
        user = AuthUserFactory()
        data = self.create(contributor=user)
        res = self.app.post_json_api(data['reg_url'], payload(name="test", text='Citation'), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 0)

    def test_create_private_reg_citation_non_admin(self):
        user = AuthUserFactory()
        data = self.create(public=False, contributor=user)
        res = self.app.post_json_api(data['reg_url'], payload(name="test", text='Citation'), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 0)

    def test_create_public_reg_citation_non_contrib(self):
        user = AuthUserFactory()
        data = self.create()
        res = self.app.post_json_api(data['reg_url'], payload(name="test", text='Citation'), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 0)

    def test_create_private_reg_citation_non_contrib(self):
        user = AuthUserFactory()
        data = self.create(public=False)
        res = self.app.post_json_api(data['reg_url'], payload(name="test", text='Citation'), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 0)

    def test_create_public_reg_citation_logged_out(self):
        data = self.create()
        res = self.app.post_json_api(data['reg_url'], payload(name="test", text='Citation'), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(len(data['registration'].alternativeCitations), 0)

    def test_create_private_reg_citation_logged_out(self):
        data = self.create(public=False)
        res = self.app.post_json_api(data['reg_url'], payload(name="test", text='Citation'), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(len(data['registration'].alternativeCitations), 0)

    def test_update_public_reg_citation_admin(self):
        data = self.create(citation=True)
        res = self.app.put_json_api(data['citation_url'], payload(name="test", text='Citation', _id=data['citation']._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(data['citation'].name, "name")
        assert_equal(data['citation'].text, "text")

    def test_update_private_reg_citation_admin(self):
        data = self.create(public=False, citation=True)
        res = self.app.put_json_api(data['citation_url'], payload(name="test", text='Citation', _id=data['citation']._id), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(data['citation'].name, "name")
        assert_equal(data['citation'].text, "text")

    def test_update_public_reg_citation_non_admin(self):
        user = AuthUserFactory()
        data = self.create(contributor=user, citation=True)
        res = self.app.put_json_api(data['citation_url'], payload(name="test", text='Citation', _id=data['citation']._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(data['citation'].name, "name")
        assert_equal(data['citation'].text, "text")

    def test_update_private_reg_citation_non_admin(self):
        user = AuthUserFactory()
        data = self.create(public=False, contributor=user, citation=True)
        res = self.app.put_json_api(data['citation_url'], payload(name="test", text='Citation', _id=data['citation']._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(data['citation'].name, "name")
        assert_equal(data['citation'].text, "text")

    def test_update_public_reg_citation_non_contrib(self):
        user = AuthUserFactory()
        data = self.create(citation=True)
        res = self.app.put_json_api(data['citation_url'], payload(name="test", text='Citation', _id=data['citation']._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(data['citation'].name, "name")
        assert_equal(data['citation'].text, "text")

    def test_update_private_reg_citation_non_contrib(self):
        user = AuthUserFactory()
        data = self.create(public=False, citation=True)
        res = self.app.put_json_api(data['citation_url'], payload(name="test", text='Citation', _id=data['citation']._id), auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(data['citation'].name, "name")
        assert_equal(data['citation'].text, "text")

    def test_update_public_reg_citation_logged_out(self):
        data = self.create(citation=True)
        res = self.app.put_json_api(data['citation_url'], payload(name="test", text='Citation', _id=data['citation']._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(data['citation'].name, "name")
        assert_equal(data['citation'].text, "text")

    def test_update_private_reg_citation_logged_out(self):
        data = self.create(public=False, citation=True)
        res = self.app.put_json_api(data['citation_url'], payload(name="test", text='Citation', _id=data['citation']._id), expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(data['citation'].name, "name")
        assert_equal(data['citation'].text, "text")

    def test_delete_public_reg_citation_admin(self):
        data = self.create(citation=True)
        res = self.app.delete(data['citation_url'], auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 1)

    def test_delete_private_reg_citation_admin(self):
        data = self.create(public=False, citation=True)
        res = self.app.delete(data['citation_url'], auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 1)

    def test_delete_public_reg_citation_non_admin(self):
        user = AuthUserFactory()
        data = self.create(contributor=user, citation=True)
        res = self.app.delete(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 1)

    def test_delete_private_reg_citation_non_admin(self):
        user = AuthUserFactory()
        data = self.create(public=False, contributor=user, citation=True)
        res = self.app.delete(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 1)

    def test_delete_public_reg_citation_non_contrib(self):
        user = AuthUserFactory()
        data = self.create(citation=True)
        res = self.app.delete(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 1)

    def test_delete_private_reg_citation_non_contrib(self):
        user = AuthUserFactory()
        data = self.create(public=False, citation=True)
        res = self.app.delete(data['citation_url'], auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
        assert_equal(len(data['registration'].alternativeCitations), 1)

    def test_delete_public_reg_citation_logged_out(self):
        data = self.create(citation=True)
        res = self.app.delete(data['citation_url'], expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(len(data['registration'].alternativeCitations), 1)

    def test_delete_private_reg_citation_logged_out(self):
        data = self.create(public=False, citation=True)
        res = self.app.delete(data['citation_url'], expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(len(res.json['errors']), 1)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')
        assert_equal(len(data['registration'].alternativeCitations), 1)
