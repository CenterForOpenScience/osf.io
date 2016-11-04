from nose.tools import *  # flake8: noqa
import pytest

from framework.auth.core import Auth
from framework.mongo import database as db
from tests.base import ApiTestCase
from api.base.settings.defaults import API_BASE
from api.base.exceptions import Conflict

from website.files.models.osfstorage import OsfStorageFile
from osf_tests.factories import PreprintFactory, AuthUserFactory, ProjectFactory, SubjectFactory
from website.preprints.model import PreprintService
from api_tests import utils as test_utils

def build_preprint_update_payload(node_id, attributes=None, relationships=None):
    payload = {
        "data": {
            "id": node_id,
            "attributes": attributes,
            "relationships": relationships
        }
    }
    return payload


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

class TestPreprintDelete(ApiTestCase):
    def setUp(self):
        super(TestPreprintDelete, self).setUp()
        self.user = AuthUserFactory()
        self.unpublished_preprint = PreprintFactory(creator=self.user, is_published=False)
        self.published_preprint = PreprintFactory(creator=self.user)
        self.url = '/{}preprints/{{}}/'.format(API_BASE)

    def test_can_delete_unpublished(self):
        previous_ids = [doc['_id'] for doc in db['preprintservice'].find({}, {'_id':1})]
        self.app.delete(self.url.format(self.unpublished_preprint._id), auth=self.user.auth)
        remaining_ids = [doc['_id'] for doc in db['preprintservice'].find({}, {'_id':1})]
        assert_in(self.unpublished_preprint._id, previous_ids)
        assert_not_in(self.unpublished_preprint._id, remaining_ids)

    def test_cannot_delete_published(self):
        previous_ids = [doc['_id'] for doc in db['preprintservice'].find({}, {'_id':1})]
        res = self.app.delete(self.url.format(self.published_preprint._id), auth=self.user.auth, expect_errors=True)
        remaining_ids = [doc['_id'] for doc in db['preprintservice'].find({}, {'_id':1})]
        assert_equal(res.status_code, 409)
        assert_equal(previous_ids, remaining_ids)
        assert_in(self.published_preprint._id, remaining_ids)

    def test_deletes_only_requested_document(self):
        previous_ids = [doc['_id'] for doc in db['preprintservice'].find({}, {'_id':1})]
        res = self.app.delete(self.url.format(self.unpublished_preprint._id), auth=self.user.auth)
        remaining_ids = [doc['_id'] for doc in db['preprintservice'].find({}, {'_id':1})]

        assert_in(self.unpublished_preprint._id, previous_ids)
        assert_in(self.published_preprint._id, previous_ids)

        assert_not_in(self.unpublished_preprint._id, remaining_ids)
        assert_in(self.published_preprint._id, remaining_ids)


class TestPreprintUpdate(ApiTestCase):
    def setUp(self):
        super(TestPreprintUpdate, self).setUp()
        self.user = AuthUserFactory()

        self.preprint = PreprintFactory(creator=self.user)
        self.url = '/{}preprints/{}/'.format(API_BASE, self.preprint._id)

        self.subject = SubjectFactory()

    def test_update_preprint_permission_denied(self):
        update_doi_payload = build_preprint_update_payload(self.preprint._id, attributes={'article_doi': '10.123/456/789'})

        noncontrib = AuthUserFactory()

        res = self.app.patch_json_api(self.url, update_doi_payload, auth=noncontrib.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.patch_json_api(self.url, update_doi_payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_update_subjects(self):
        assert_not_equal(self.preprint.subjects[0], [self.subject._id])
        update_subjects_payload = build_preprint_update_payload(self.preprint._id, attributes={"subjects": [[self.subject._id]]})

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.preprint.reload()
        assert_equal(self.preprint.subjects.first(), [self.subject._id])

    def test_update_invalid_subjects(self):
        subjects = self.preprint.subjects
        update_subjects_payload = build_preprint_update_payload(self.preprint._id, attributes={"subjects": [['wwe']]})

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.preprint.reload()
        assert_equal(self.preprint.subjects, subjects)

    @pytest.mark.skip('Unskip when StoredFileNode is implemented')
    def test_update_primary_file(self):
        new_file = test_utils.create_test_file(self.preprint.node, 'openupthatwindow.pdf')
        relationships = {
            "primary_file": {
                "data": {
                    "type": "file",
                    "id": new_file._id
                }
            }
        }
        assert_not_equal(self.preprint.primary_file, new_file)
        update_file_payload = build_preprint_update_payload(self.preprint._id, relationships=relationships)

        res = self.app.patch_json_api(self.url, update_file_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.preprint.node.reload()
        assert_equal(self.preprint.primary_file, new_file)

    @pytest.mark.skip('Unskip when StoredFileNode is implemented')
    def test_new_primary_not_in_node(self):
        project = ProjectFactory()
        file_for_project = test_utils.create_test_file(project, 'letoutthatantidote.pdf')

        relationships = {
            "primary_file": {
                "data": {
                    "type": "file",
                    "id": file_for_project._id
                }
            }
        }

        update_file_payload = build_preprint_update_payload(self.preprint._id, relationships=relationships)

        res = self.app.patch_json_api(self.url, update_file_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.preprint.reload()
        assert_not_equal(self.preprint.primary_file, file_for_project)

    def test_update_doi(self):
        new_doi = '10.1234/ASDFASDF'
        assert_not_equal(self.preprint.article_doi, new_doi)
        update_subjects_payload = build_preprint_update_payload(self.preprint._id, attributes={"doi": new_doi})

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.preprint.node.reload()
        assert_equal(self.preprint.article_doi, new_doi)

        preprint_detail = self.app.get(self.url, auth=self.user.auth).json['data']
        assert_equal(preprint_detail['links']['doi'], 'https://dx.doi.org/{}'.format(new_doi))

    def test_write_contrib_cannot_set_primary_file(self):
        user_two = AuthUserFactory()
        self.preprint.node.add_contributor(user_two, permissions=['read', 'write'], auth=Auth(self.user), save=True)
        new_file = test_utils.create_test_file(self.preprint.node, 'openupthatwindow.pdf')

        data = {
            'data':{
                'type': 'primary_file',
                'id': self.preprint._id,
                'attributes': {},
                'relationships': {
                    'primary_file': {
                        'data': {
                            'type': 'file',
                            'id': new_file._id
                        }
                    }
                }
            }
        }

        res = self.app.patch_json_api(self.url, data, auth=user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_noncontrib_cannot_set_primary_file(self):
        user_two = AuthUserFactory()
        new_file = test_utils.create_test_file(self.preprint.node, 'openupthatwindow.pdf')

        data = {
            'data':{
                'type': 'primary_file',
                'id': self.preprint._id,
                'attributes': {},
                'relationships': {
                    'primary_file': {
                        'data': {
                            'type': 'file',
                            'id': new_file._id
                        }
                    }
                }
            }
        }

        res = self.app.patch_json_api(self.url, data, auth=user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_write_contrib_cannot_set_subjects(self):
        user_two = AuthUserFactory()
        self.preprint.node.add_contributor(user_two, permissions=['read', 'write'], auth=Auth(self.user), save=True)

        assert_not_equal(self.preprint.subjects.first(), self.subject._id)
        update_subjects_payload = build_preprint_update_payload(self.preprint._id, attributes={"subjects": [[self.subject._id]]})

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        assert_not_equal(self.preprint.subjects[0], self.subject._id)

    def test_noncontrib_cannot_set_subjects(self):
        user_two = AuthUserFactory()
        self.preprint.node.add_contributor(user_two, permissions=['read', 'write'], auth=Auth(self.user), save=True)

        assert_not_equal(self.preprint.subjects.first(), self.subject._id)
        update_subjects_payload = build_preprint_update_payload(self.preprint._id, attributes={"subjects": [[self.subject._id]]})

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        assert_not_equal(self.preprint.subjects.first(), self.subject._id)
