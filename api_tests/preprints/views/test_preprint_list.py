from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth, Q
from api.base.settings.defaults import API_BASE
from website.util import permissions
from website.models import Node
from website.preprints.model import PreprintService
from website.project import signals as project_signals


from tests.base import ApiTestCase, capture_signals
from tests.factories import (
    ProjectFactory,
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory
)

from api_tests import utils as test_utils

def build_preprint_create_payload(node_id=None, provider_id=None, file_id=None, attrs={}):
    payload = {
        "data": {
            "attributes": attrs,
            "relationships": {},            
            "type": "preprints"
        }
    }
    if node_id:
        payload['data']['relationships']["node"] = {
            "data": {
                "type": "node",
                "id": node_id
            }
        }
    if provider_id:
        payload['data']['relationships']["provider"] = {
            "data": {
                "type": "provider",
                "id": provider_id
            }
        }
    if file_id:
        payload['data']['relationships']["primary_file"] = {
            "data": {
                "type": "primary_file",
                "id": file_id
            }
        }
    return payload

class TestPreprintList(ApiTestCase):

    def setUp(self):
        super(TestPreprintList, self).setUp()
        self.user = AuthUserFactory()

        self.preprint = PreprintFactory(creator=self.user)
        self.url = '/{}preprints/'.format(API_BASE)

        self.project = ProjectFactory(creator=self.user)

    def tearDown(self):
        super(TestPreprintList, self).tearDown()
        Node.remove()
        PreprintService.remove()

    def test_return_preprints_logged_out(self):
        res = self.app.get(self.url)
        assert_equal(len(res.json['data']), 1)
        assert_equal(res.status_code, 200)
        assert_equal(res.status_code, 200)
        assert_equal(res.content_type, 'application/vnd.api+json')

    def test_exclude_nodes_from_preprints_endpoint(self):
        res = self.app.get(self.url, auth=self.user.auth)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.preprint._id, ids)
        assert_not_in(self.project._id, ids)


class TestPreprintFiltering(ApiTestCase):

    def setUp(self):
        super(TestPreprintFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.provider = PreprintProviderFactory(name='wwe')
        self.provider_two = PreprintProviderFactory(name='wcw')

        self.subject = SubjectFactory()
        self.subject_two = SubjectFactory()

        self.preprint = PreprintFactory(creator=self.user, provider=self.provider, subjects=[[self.subject._id]])
        self.preprint_two = PreprintFactory(creator=self.user, filename='woo.txt', provider=self.provider_two, subjects=[[self.subject_two._id]])
        self.preprint_three = PreprintFactory(creator=self.user, filename='stonecold.txt', provider=self.provider, subjects=[[self.subject._id], [self.subject_two._id]])

    def tearDown(self):
        super(TestPreprintFiltering, self).tearDown()
        Node.remove()

    def test_filter_by_provider(self):
        url = '/{}preprints/?filter[provider]={}'.format(API_BASE, self.provider._id)
        res = self.app.get(url, auth=self.user.auth)
        ids = [datum['id'] for datum in res.json['data']]

        assert_in(self.preprint._id, ids)
        assert_not_in(self.preprint_two._id, ids)
        assert_in(self.preprint_three._id, ids)

class TestPreprintCreate(ApiTestCase):
    def setUp(self):
        super(TestPreprintCreate, self).setUp()

        self.user = AuthUserFactory()
        self.other_user = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user)
        self.public_project = ProjectFactory(creator=self.user, public=True)
        self.public_project.add_contributor(self.other_user, permissions=[permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS], save=True)
        self.subject = SubjectFactory()
        self.provider = PreprintProviderFactory()

        self.user_two = AuthUserFactory()

        self.file_one_public_project = test_utils.create_test_file(self.public_project, self.user, 'millionsofdollars.pdf')
        self.file_one_private_project = test_utils.create_test_file(self.private_project, self.user, 'woowoowoo.pdf')

        self.url = '/{}preprints/'.format(API_BASE)

    def test_create_preprint_from_public_project(self):
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.provider._id, self.file_one_public_project._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth)

        assert_equal(res.status_code, 201)

    def test_create_preprint_from_private_project(self):
        private_project_payload = build_preprint_create_payload(self.private_project._id, self.provider._id, self.file_one_private_project._id, attrs={
                'subjects': [[SubjectFactory()._id]],
                'is_published': True
            })
        res = self.app.post_json_api(self.url, private_project_payload, auth=self.user.auth)

        self.private_project.reload()
        assert_equal(res.status_code, 201)
        assert_true(self.private_project.is_public)

    def test_non_authorized_user(self):
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.provider._id, self.file_one_public_project._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user_two.auth, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_read_write_user_not_admin(self):
        assert_in(self.other_user, self.public_project.contributors)
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.provider._id, self.file_one_public_project._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.other_user.auth, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_file_is_not_in_node(self):
        wrong_project_payload = build_preprint_create_payload(self.public_project._id, self.provider._id, self.file_one_private_project._id)
        res = self.app.post_json_api(self.url, wrong_project_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This file is not a valid primary file for this preprint.')

    def test_already_a_preprint_with_conflicting_provider(self):
        preprint = PreprintFactory(creator=self.user)
        file_one_preprint = test_utils.create_test_file(preprint.node, self.user, 'openupthatwindow.pdf')

        already_preprint_payload = build_preprint_create_payload(preprint.node._id, preprint.provider._id, file_one_preprint._id)
        res = self.app.post_json_api(self.url, already_preprint_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 409)
        assert_in('Only one preprint per provider can be submitted for a node.', res.json['errors'][0]['detail'])

    def test_read_write_user_already_a_preprint_with_conflicting_provider(self):
        assert_in(self.other_user, self.public_project.contributors)

        preprint = PreprintFactory(creator=self.user)
        preprint.node.add_contributor(self.other_user, permissions=[permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS], save=True)
        file_one_preprint = test_utils.create_test_file(preprint.node, self.user, 'openupthatwindow.pdf')

        already_preprint_payload = build_preprint_create_payload(preprint.node._id, self.provider._id, file_one_preprint._id)
        res = self.app.post_json_api(self.url, already_preprint_payload, auth=self.other_user.auth, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_no_primary_file_passed(self):
        no_file_payload = build_preprint_create_payload(self.public_project._id, self.provider._id)

        res = self.app.post_json_api(self.url, no_file_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'You must specify a valid primary_file to create a preprint.')

    def test_invalid_primary_file(self):
        invalid_file_payload = build_preprint_create_payload(self.public_project._id, self.provider._id, 'totallynotanid')
        res = self.app.post_json_api(self.url, invalid_file_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'You must specify a valid primary_file to create a preprint.')

    def test_no_provider_given(self):
        no_providers_payload = build_preprint_create_payload(self.public_project._id, self.provider._id, self.file_one_public_project._id)
        del no_providers_payload['data']['relationships']['provider']
        res = self.app.post_json_api(self.url, no_providers_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'You must specify a valid provider to create a preprint.')

    def test_invalid_provider_given(self):
        wrong_provider_payload = build_preprint_create_payload(self.public_project._id, 'jobbers', self.file_one_public_project._id)

        res = self.app.post_json_api(self.url, wrong_provider_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'You must specify a valid provider to create a preprint.')

    def test_request_id_does_not_match_request_url_id(self):
        public_project_payload = build_preprint_create_payload(self.private_project._id, self.provider._id, self.file_one_public_project._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This file is not a valid primary file for this preprint.')

    def test_file_not_osfstorage(self):
        github_file = self.file_one_public_project
        github_file.provider = 'github'
        github_file.save()
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.provider._id, github_file._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This file is not a valid primary file for this preprint.')

    def test_preprint_contributor_signal_not_sent_on_creation(self):
        with capture_signals() as mock_signals:
            public_project_payload = build_preprint_create_payload(self.public_project._id, self.provider._id,
                                                                   self.file_one_public_project._id)
            res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth)

            assert_equal(res.status_code, 201)
            assert_not_in(project_signals.contributor_added, mock_signals.signals_sent())

    def test_create_preprint_with_deleted_node_should_fail(self):
        self.public_project.is_deleted = True
        self.public_project.save()
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.provider._id, self.file_one_public_project._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Cannot create a preprint from a deleted node.')

    def test_create_preprint_adds_log_if_published(self):
        public_project_payload = build_preprint_create_payload(
            self.public_project._id,
            self.provider._id,
            self.file_one_public_project._id,
            {
                'is_published': True,
                'subjects': [[SubjectFactory()._id]],
            }
        )
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        preprint_id = res.json['data']['id']
        preprint = PreprintService.load(preprint_id)
        log = preprint.node.logs[-2]
        assert_equal(log.action, 'preprint_initiated')
        assert_equal(log.params.get('preprint'), preprint_id)
