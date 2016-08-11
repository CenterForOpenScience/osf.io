from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from api.base.settings.defaults import API_BASE

from website.files.models.osfstorage import OsfStorageFile
from tests.factories import PreprintFactory, AuthUserFactory, ProjectFactory, SubjectFactory


class TestPreprintDetail(ApiTestCase):
    def setUp(self):
        super(TestPreprintDetail, self).setUp()

        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)
        self.url = '/{}preprints/{}/'.format(API_BASE, self.preprint._id)
        self.res = self.app.get(self.url)
        self.data = self.res.json['data']

    def test_preprint_detail_success(self):
        assert_equal(self.res.status_code, 200)
        assert_equal(self.res.content_type, 'application/vnd.api+json')

    def test_preprint_top_level(self):
        assert_equal(self.data['type'], 'preprints')
        assert_equal(self.data['id'], self.preprint._id)


def create_file(node, filename):
    file = OsfStorageFile.create(
        is_file=True,
        node=node,
        path='/{}'.format(filename),
        name=filename,
        materialized_path='/{}'.format(filename))
    file.save()
    return file


def build_preprint_payload(node_id, subject_id, file_id=None):
    payload = {
        "data": {
            "id": node_id,
            "attributes": {
                "subjects": [subject_id]
            }
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


class TestPreprintCreate(ApiTestCase):
    def setUp(self):
        super(TestPreprintCreate, self).setUp()

        self.user = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user)
        self.public_project = ProjectFactory(creator=self.user, public=True)
        self.subject = SubjectFactory()

        self.user_two = AuthUserFactory()

        self.file_one_public_project = create_file(self.public_project, 'millionsofdollars.pdf')
        self.file_one_private_project = create_file(self.private_project, 'woowoowoo.pdf')

    def test_create_preprint_from_public_project(self):
        public_project_payload = build_preprint_payload(self.public_project._id, self.subject._id, self.file_one_public_project._id)
        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, public_project_payload, auth=self.user.auth)

        assert_equal(res.status_code, 201)

    def test_create_preprint_from_private_project(self):
        private_project_payload = build_preprint_payload(self.private_project._id, self.subject._id, self.file_one_private_project._id)
        url = '/{}preprints/{}/'.format(API_BASE, self.private_project._id)
        res = self.app.post_json_api(url, private_project_payload, auth=self.user.auth)

        self.private_project.reload()
        assert_equal(res.status_code, 201)
        assert_true(self.private_project.is_public)

    def test_non_authorized_user(self):
        public_project_payload = build_preprint_payload(self.public_project._id, self.subject._id, self.file_one_public_project._id)
        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, public_project_payload, auth=self.user_two.auth, expect_errors=True)

        assert_equal(res.status_code, 403)

    def test_file_is_not_in_node(self):
        wrong_project_payload = build_preprint_payload(self.public_project._id, self.subject._id,  self.file_one_private_project._id)
        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, wrong_project_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)

    def test_already_a_preprint(self):
        preprint = PreprintFactory(creator=self.user)
        file_one_preprint = create_file(preprint, 'openupthatwindow.pdf')

        already_preprint_payload = build_preprint_payload(preprint._id,  self.subject._id, file_one_preprint._id)
        url = '/{}preprints/{}/'.format(API_BASE, preprint._id)
        res = self.app.post_json_api(url, already_preprint_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 409)

    def test_no_primary_file_passed(self):
        no_file_payload = build_preprint_payload(self.public_project._id,  self.subject._id)

        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, no_file_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)

    def test_invalid_primary_file(self):
        invalid_file_payload = build_preprint_payload(self.public_project._id,  self.subject._id, 'totallynotanid')
        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, invalid_file_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)

    def test_no_subjects_given(self):
        no_subjects_payload = build_preprint_payload(self.public_project._id,  self.subject._id, self.file_one_public_project._id)
        del no_subjects_payload['data']['attributes']['subjects']

        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, no_subjects_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)

    def test_invalid_subjects_given(self):
        wrong_subjects_payload = build_preprint_payload(self.public_project._id,  self.subject._id, self.file_one_public_project._id)
        wrong_subjects_payload['data']['attributes']['subjects'] = ['jobbers']

        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, wrong_subjects_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)

    def test_request_id_does_not_match_request_url_id(self):
        public_project_payload = build_preprint_payload(self.private_project._id,  self.subject._id, self.file_one_public_project._id)
        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, public_project_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)

    def test_file_not_osfstorage(self):
        github_file = self.file_one_public_project
        github_file.provider = 'github'
        github_file.save()
        public_project_payload = build_preprint_payload(self.public_project._id,  self.subject._id, github_file._id)
        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, public_project_payload, auth=self.user.auth, expect_errors=True)

        assert_equal(res.status_code, 400)


class TestPreprintUpdate(ApiTestCase):
    def setUp(self):
        super(TestPreprintUpdate, self).setUp()
        self.user = AuthUserFactory()

        self.preprint = PreprintFactory(creator=self.user)
        self.url = '/{}preprints/{}/'.format(API_BASE, self.preprint._id)

        self.file_preprint = create_file(self.preprint, 'openupthatwindow.pdf')

        self.subject = SubjectFactory()

    def test_update_preprint_title(self):
        update_title_payload = build_preprint_payload(self.preprint._id,  self.subject._id,)
        update_title_payload['data']['attributes'] = {'title': 'A new title'}
        update_title_payload['data']['attributes']['subjects'] = [self.subject._id]

        res = self.app.patch_json_api(self.url, update_title_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.preprint.reload()
        assert_equal(self.preprint.title, 'A new title')

    def test_update_preprint_subjects(self):
        update_subjects_payload = build_preprint_payload(self.preprint._id,  self.subject._id,)
        update_subjects_payload['data']['attributes']['subjects'] = [self.subject._id]

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.preprint.reload()
        assert_equal(self.preprint.preprint_subjects[0], self.subject._id)

    def test_update_invalid_subjects(self):
        preprint_subjects = self.preprint.preprint_subjects
        update_subjects_payload = build_preprint_payload(self.preprint._id, self.subject._id)
        update_subjects_payload['data']['attributes']['subjects'] = ['wwe']

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.preprint.reload()
        assert_equal(self.preprint.preprint_subjects, preprint_subjects)

    def test_update_primary_file(self):
        assert_not_equal(self.preprint.preprint_file, self.file_preprint)
        update_file_payload = build_preprint_payload(self.preprint._id, self.subject._id, file_id=self.file_preprint._id)

        res = self.app.patch_json_api(self.url, update_file_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.preprint.reload()
        assert_equal(self.preprint.preprint_file, self.file_preprint)

    def test_new_primary_not_in_node(self):
        project = ProjectFactory()
        file_for_project = create_file(project, 'letoutthatantidote.pdf')

        update_file_payload = build_preprint_payload(self.preprint._id, self.subject._id, file_id=file_for_project._id)

        res = self.app.patch_json_api(self.url, update_file_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.preprint.reload()
        assert_not_equal(self.preprint.preprint_file, file_for_project)
