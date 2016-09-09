from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth, Q
from api.base.settings.defaults import API_BASE
from website.util import permissions
from website.models import Node
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

def build_preprint_create_payload(node_id, subject_id, file_id=None):
    payload = {
        "data": {
            "id": node_id,
            "attributes": {
                "subjects": [subject_id],
                "abstract": "Much preprint. Very open. Wow"
            },
            "type": "preprints"
        }
    }
    if file_id:
        payload['data']['relationships'] = {
            "primary_file": {
                "data": {
                    "type": "file",
                    "id": file_id
                }
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
        self.preprint = PreprintFactory(creator=self.user, providers=[self.provider])

        self.preprint.add_tag('nature boy', Auth(self.user), save=False)
        self.preprint.add_tag('ric flair', Auth(self.user), save=False)
        self.preprint.save()

        self.provider_two = PreprintProviderFactory(name='wcw')
        self.preprint_two = PreprintFactory(creator=self.user, filename='woo.txt', providers=[self.provider_two])
        self.preprint_two.add_tag('nature boy', Auth(self.user), save=False)
        self.preprint_two.add_tag('woo', Auth(self.user), save=False)
        self.preprint_two.save()

        self.preprint_three = PreprintFactory(creator=self.user, filename='stonecold.txt', providers=[self.provider])
        self.preprint_three.add_tag('stone', Auth(self.user), save=False)
        self.preprint_two.add_tag('cold', Auth(self.user), save=False)
        self.preprint_three.save()

    def tearDown(self):
        super(TestPreprintFiltering, self).tearDown()
        Node.remove()

    def test_filtering_tags(self):
        # both preprint and preprint_two have nature boy
        url = '/{}preprints/?filter[tags]={}'.format(API_BASE, 'nature boy')

        res = self.app.get(url, auth=self.user.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.preprint._id, ids)
        assert_in(self.preprint_two._id, ids)
        assert_not_in(self.preprint_three._id, ids)

        # filtering two tags
        # preprint has both tags; preprint_two only has one
        url = '/{}preprints/?filter[tags]={}&filter[tags]={}'.format(API_BASE, 'nature boy', 'ric flair')

        res = self.app.get(url, auth=self.user.auth)
        reg_json = res.json['data']

        ids = [each['id'] for each in reg_json]
        assert_in(self.preprint._id, ids)
        assert_not_in(self.preprint_two._id, ids)
        assert_not_in(self.preprint_three._id, ids)

    def test_filter_by_doi(self):
        url = '/{}preprints/?filter[doi]={}'.format(API_BASE, self.preprint.preprint_doi)

        res = self.app.get(url, auth=self.user.auth)
        data = res.json['data']

        assert_equal(len(data), 1)
        for result in data:
            assert_equal(self.preprint._id, result['id'])


class TestPreprintCreate(ApiTestCase):
    def setUp(self):
        super(TestPreprintCreate, self).setUp()

        self.user = AuthUserFactory()
        self.other_user = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user)
        self.public_project = ProjectFactory(creator=self.user, public=True)
        self.public_project.add_contributor(self.other_user, permissions=[permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS], save=True)
        self.subject = SubjectFactory()

        self.user_two = AuthUserFactory()

        self.file_one_public_project = test_utils.create_test_file(self.public_project, self.user, 'millionsofdollars.pdf')
        self.file_one_private_project = test_utils.create_test_file(self.private_project, self.user, 'woowoowoo.pdf')

        self.url = '/{}preprints/'.format(API_BASE)

    def test_create_preprint_from_public_project(self):
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.subject._id, self.file_one_public_project._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth)

        assert_equal(res.status_code, 201)

    def test_create_preprint_with_tags(self):
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.subject._id, self.file_one_public_project._id)
        public_project_payload['data']['attributes']['tags'] = ['newtag', 'bluetag']
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth)

        assert_equal(res.status_code, 201)

        self.public_project.reload()
        assert_in('newtag', self.public_project.tags)
        assert_in('bluetag', self.public_project.tags)
        assert_not_in('tag_added', [l.action for l in self.public_project.logs])

    def test_create_preprint_from_private_project(self):
        private_project_payload = build_preprint_create_payload(self.private_project._id, self.subject._id, self.file_one_private_project._id)
        res = self.app.post_json_api(self.url, private_project_payload, auth=self.user.auth)

        self.private_project.reload()
        assert_equal(res.status_code, 201)
        assert_true(self.private_project.is_public)

    def test_non_authorized_user(self):
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.subject._id, self.file_one_public_project._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user_two.auth, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_read_write_user_not_admin(self):
        assert_in(self.other_user, self.public_project.contributors)
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.subject._id, self.file_one_public_project._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.other_user.auth, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_file_is_not_in_node(self):
        wrong_project_payload = build_preprint_create_payload(self.public_project._id, self.subject._id, self.file_one_private_project._id)
        res = self.app.post_json_api(self.url, wrong_project_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This file is not a valid primary file for this preprint.')

    def test_already_a_preprint(self):
        preprint = PreprintFactory(creator=self.user)
        file_one_preprint = test_utils.create_test_file(preprint, self.user, 'openupthatwindow.pdf')

        already_preprint_payload = build_preprint_create_payload(preprint._id, self.subject._id, file_one_preprint._id)
        res = self.app.post_json_api(self.url, already_preprint_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'This node already stored as a preprint, use the update method instead.')

    def test_read_write_user_already_a_preprint(self):
        assert_in(self.other_user, self.public_project.contributors)

        preprint = PreprintFactory(creator=self.user)
        preprint.add_contributor(self.other_user, permissions=[permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS], save=True)
        file_one_preprint = test_utils.create_test_file(preprint, self.user, 'openupthatwindow.pdf')

        already_preprint_payload = build_preprint_create_payload(preprint._id, self.subject._id, file_one_preprint._id)
        res = self.app.post_json_api(self.url, already_preprint_payload, auth=self.other_user.auth, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_no_primary_file_passed(self):
        no_file_payload = build_preprint_create_payload(self.public_project._id, self.subject._id)

        res = self.app.post_json_api(self.url, no_file_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'You must specify a primary_file to create a preprint.')

    def test_invalid_primary_file(self):
        invalid_file_payload = build_preprint_create_payload(self.public_project._id, self.subject._id, 'totallynotanid')
        res = self.app.post_json_api(self.url, invalid_file_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'You must specify a primary_file to create a preprint.')

    def test_no_subjects_given(self):
        no_subjects_payload = build_preprint_create_payload(self.public_project._id, self.subject._id, self.file_one_public_project._id)
        del no_subjects_payload['data']['attributes']['subjects']
        res = self.app.post_json_api(self.url, no_subjects_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'You must specify at least one subject to create a preprint.')

    def test_invalid_subjects_given(self):
        wrong_subjects_payload = build_preprint_create_payload(self.public_project._id, self.subject._id, self.file_one_public_project._id)
        wrong_subjects_payload['data']['attributes']['subjects'] = ['jobbers']

        res = self.app.post_json_api(self.url, wrong_subjects_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Subject with id <jobbers> could not be found.')

    def test_request_id_does_not_match_request_url_id(self):
        public_project_payload = build_preprint_create_payload(self.private_project._id, self.subject._id, self.file_one_public_project._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This file is not a valid primary file for this preprint.')

    def test_file_not_osfstorage(self):
        github_file = self.file_one_public_project
        github_file.provider = 'github'
        github_file.save()
        public_project_payload = build_preprint_create_payload(self.public_project._id, self.subject._id, github_file._id)
        res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This file is not a valid primary file for this preprint.')

    def test_preprint_contributor_signal_sent_on_creation(self):
        with capture_signals() as mock_signals:
            public_project_payload = build_preprint_create_payload(self.public_project._id, self.subject._id,
                                                                   self.file_one_public_project._id)
            res = self.app.post_json_api(self.url, public_project_payload, auth=self.user.auth)

            assert_equal(res.status_code, 201)
            assert_equal(mock_signals.signals_sent(), set([project_signals.contributor_added]))

    def test_preprint_contributor_signal_not_sent_one_contributor(self):
        with capture_signals() as mock_signals:
            private_project_payload = build_preprint_create_payload(self.private_project._id, self.subject._id,
                                                                   self.file_one_private_project._id)
            res = self.app.post_json_api(self.url, private_project_payload, auth=self.user.auth)
            assert_equal(res.status_code, 201)
            assert_not_equal(mock_signals.signals_sent(), set([project_signals.contributor_added]))
