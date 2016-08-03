from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from api.base.settings.defaults import API_BASE

from website.files.models.osfstorage import OsfStorageFile
from tests.factories import PreprintFactory, AuthUserFactory, ProjectFactory


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


def create_preprint_file(node, filename):
    file = OsfStorageFile.create(
        is_file=True,
        node=node,
        path='/{}'.format(filename),
        name=filename,
        materialized_path='/{}'.format(filename))
    file.save()
    return file


def build_preprint_payload(node_id, file_id):
    return {
        "data": {
            "id": node_id,
            "attributes": {
                "subjects": ["biology"]
            },
            "relationships": {
                "preprint_file": {
                    "data": {
                        "type": "primary_file",
                        "id": file_id
                    }
                }
            }
        }
    }


class TestPreprintUpdate(ApiTestCase):
    def setUp(self):
        super(TestPreprintUpdate, self).setUp()

        self.user = AuthUserFactory()
        self.private_project = ProjectFactory(creator=self.user)
        self.public_project = ProjectFactory(creator=self.user, public=True)

        self.file_one_public_project = create_preprint_file(self.public_project, 'millionsofdollars.pdf')
        self.file_one_private_project = create_preprint_file(self.private_project, 'woowoowoo.pdf')

        self.preprint = PreprintFactory(creator=self.user)

    def test_create_preprint_from_public_project(self):
        public_project_payload = build_preprint_payload(self.public_project._id, self.file_one_public_project._id)
        url = '/{}preprints/{}/'.format(API_BASE, self.public_project._id)
        res = self.app.post_json_api(url, public_project_payload, auth=self.user.auth)

        assert_equal(res.status_code, 201)

    def test_create_preprint_from_private_project(self):
        private_project_payload = build_preprint_payload(self.private_project._id, self.file_one_private_project._id)
        url = '/{}preprints/{}/'.format(API_BASE, self.private_project._id)
        res = self.app.post_json_api(url, private_project_payload, auth=self.user.auth)

        assert_equal(res.status_code, 201)
