import functools
from modularodm import Q
from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from framework.mongo import database as db
from tests.base import ApiTestCase
from api.base.settings.defaults import API_BASE

from website.project.licenses import NodeLicense, ensure_licenses
from tests.factories import PreprintFactory, AuthUserFactory, ProjectFactory, SubjectFactory, PreprintProviderFactory
from api_tests import utils as test_utils

ensure_licenses = functools.partial(ensure_licenses, warn=False)

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
        assert_equal(self.preprint.subjects[0], [self.subject._id])

    def test_update_invalid_subjects(self):
        subjects = self.preprint.subjects
        update_subjects_payload = build_preprint_update_payload(self.preprint._id, attributes={"subjects": [['wwe']]})

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.preprint.reload()
        assert_equal(self.preprint.subjects, subjects)

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

        # check logs
        log = self.preprint.node.logs[-1]
        assert_equal(log.action, 'preprint_file_updated')
        assert_equal(log.params.get('preprint'), self.preprint._id)

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
        
        assert_not_equal(self.preprint.subjects[0], self.subject._id)
        update_subjects_payload = build_preprint_update_payload(self.preprint._id, attributes={"subjects": [[self.subject._id]]})

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        assert_not_equal(self.preprint.subjects[0], self.subject._id)

    def test_noncontrib_cannot_set_subjects(self):
        user_two = AuthUserFactory()
        self.preprint.node.add_contributor(user_two, permissions=['read', 'write'], auth=Auth(self.user), save=True)
        
        assert_not_equal(self.preprint.subjects[0], self.subject._id)
        update_subjects_payload = build_preprint_update_payload(self.preprint._id, attributes={"subjects": [[self.subject._id]]})

        res = self.app.patch_json_api(self.url, update_subjects_payload, auth=user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        assert_not_equal(self.preprint.subjects[0], self.subject._id)


class TestPreprintUpdateLicense(ApiTestCase):

    def setUp(self):
        super(TestPreprintUpdateLicense, self).setUp()

        ensure_licenses()

        self.admin_contributor = AuthUserFactory()
        self.rw_contributor = AuthUserFactory()
        self.read_contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

        self.preprint_provider = PreprintProviderFactory()
        self.preprint = PreprintFactory(creator=self.admin_contributor, provider=self.preprint_provider)

        self.preprint.node.add_contributor(self.rw_contributor, auth=Auth(self.admin_contributor))
        self.preprint.node.add_contributor(self.read_contributor, auth=Auth(self.admin_contributor), permissions=['read'])
        self.preprint.node.save()

        self.cc0_license = NodeLicense.find_one(Q('name', 'eq', 'CC0 1.0 Universal'))
        self.mit_license = NodeLicense.find_one(Q('name', 'eq', 'MIT License'))
        self.no_license = NodeLicense.find_one(Q('name', 'eq', 'No license'))

        self.preprint_provider.licenses_acceptable = [self.cc0_license, self.no_license]
        self.preprint_provider.save()

        self.url = '/{}preprints/{}/'.format(API_BASE, self.preprint._id)

    def make_payload(self, node_id, license_id=None, license_year=None, copyright_holders=None):
        attributes = {}

        if license_year and copyright_holders:
            attributes = {
                'license_record': {
                    'year': license_year,
                    'copyright_holders': copyright_holders
                }
            }
        elif license_year:
            attributes = {
                'license_record': {
                    'year': license_year
                }
            }
        elif copyright_holders:
            attributes = {
                'license_record': {
                    'copyright_holders': copyright_holders
                }
            }

        return {
            'data': {
                'id': node_id,
                'attributes': attributes,
                'relationships': {
                    'license': {
                        'data': {
                            'type': 'licenses',
                            'id': license_id
                        }
                    }
                }
            }
        } if license_id else {
            'data': {
                'id': node_id,
                'attributes': attributes
            }
        }

    def make_request(self, url, data, auth=None, expect_errors=False):
        return self.app.patch_json_api(url, data, auth=auth, expect_errors=expect_errors)

    def test_admin_can_update_license(self):
        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.cc0_license._id
        )

        assert_equal(self.preprint.license, None)

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        self.preprint.reload()

        assert_equal(self.preprint.license.node_license, self.cc0_license)
        assert_equal(self.preprint.license.year, None)
        assert_equal(self.preprint.license.copyright_holders, [])

        # check logs
        log = self.preprint.node.logs[-1]
        assert_equal(log.action, 'preprint_license_updated')
        assert_equal(log.params.get('preprint'), self.preprint._id)

    def test_admin_can_update_license_record(self):
        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.no_license._id,
            license_year='2015',
            copyright_holders=['Bojack Horseman, Princess Carolyn']
        )

        assert_equal(self.preprint.license, None)

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        self.preprint.reload()

        assert_equal(self.preprint.license.node_license, self.no_license)
        assert_equal(self.preprint.license.year, '2015')
        assert_equal(self.preprint.license.copyright_holders, ['Bojack Horseman, Princess Carolyn'])

    def test_rw_contributor_cannot_update_license(self):
        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.cc0_license._id
        )

        res = self.make_request(self.url, data, auth=self.rw_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'User must be an admin to update a preprint.')

    def test_read_contributor_cannot_update_license(self):
        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.cc0_license._id
        )

        res = self.make_request(self.url, data, auth=self.read_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_non_contributor_cannot_update_license(self):
        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.cc0_license._id
        )

        res = self.make_request(self.url, data, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_unauthenticated_user_cannot_update_license(self):
        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.cc0_license._id
        )

        res = self.make_request(self.url, data, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_update_preprint_with_invalid_license_for_provider(self):
        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.mit_license._id
        )

        assert_equal(self.preprint.license, None)

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'Invalid license chosen for {}'.format(self.preprint_provider.name))

    def test_update_preprint_with_existing_license_year_attribute_only(self):
        self.preprint.set_preprint_license(
            {
                'id': self.no_license.id,
                'year': '2014',
                'copyrightHolders': ['Diane', 'Mr. Peanut Butter']
            },
            Auth(self.admin_contributor),
        )
        self.preprint.save()

        assert_equal(self.preprint.license.node_license, self.no_license)
        assert_equal(self.preprint.license.year, '2014')
        assert_equal(self.preprint.license.copyright_holders, ['Diane', 'Mr. Peanut Butter'])

        data = self.make_payload(
            node_id=self.preprint._id,
            license_year='2015'
        )

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        self.preprint.license.reload()

        assert_equal(self.preprint.license.node_license, self.no_license)
        assert_equal(self.preprint.license.year, '2015')
        assert_equal(self.preprint.license.copyright_holders, ['Diane', 'Mr. Peanut Butter'])

    def test_update_preprint_with_existing_license_copyright_holders_attribute_only(self):
        self.preprint.set_preprint_license(
            {
                'id': self.no_license.id,
                'year': '2014',
                'copyrightHolders': ['Diane', 'Mr. Peanut Butter']
            },
            Auth(self.admin_contributor),
        )
        self.preprint.save()

        assert_equal(self.preprint.license.node_license, self.no_license)
        assert_equal(self.preprint.license.year, '2014')
        assert_equal(self.preprint.license.copyright_holders, ['Diane', 'Mr. Peanut Butter'])

        data = self.make_payload(
            node_id=self.preprint._id,
            copyright_holders=['Bojack Horseman', 'Princess Carolyn']
        )

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        self.preprint.license.reload()

        assert_equal(self.preprint.license.node_license, self.no_license)
        assert_equal(self.preprint.license.year, '2014')
        assert_equal(self.preprint.license.copyright_holders, ['Bojack Horseman', 'Princess Carolyn'])

    def test_update_preprint_with_existing_license_relationship_only(self):
        self.preprint.set_preprint_license(
            {
                'id': self.no_license.id,
                'year': '2014',
                'copyrightHolders': ['Diane', 'Mr. Peanut Butter']
            },
            Auth(self.admin_contributor),
        )
        self.preprint.save()

        assert_equal(self.preprint.license.node_license, self.no_license)
        assert_equal(self.preprint.license.year, '2014')
        assert_equal(self.preprint.license.copyright_holders, ['Diane', 'Mr. Peanut Butter'])

        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.cc0_license._id
        )

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        self.preprint.license.reload()

        assert_equal(self.preprint.license.node_license, self.cc0_license)
        assert_equal(self.preprint.license.year, '2014')
        assert_equal(self.preprint.license.copyright_holders, ['Diane', 'Mr. Peanut Butter'])

    def test_update_preprint_with_existing_license_relationship_and_attributes(self):
        self.preprint.set_preprint_license(
            {
                'id': self.no_license.id,
                'year': '2014',
                'copyrightHolders': ['Diane', 'Mr. Peanut Butter']
            },
            Auth(self.admin_contributor),
            save=True
        )

        assert_equal(self.preprint.license.node_license, self.no_license)
        assert_equal(self.preprint.license.year, '2014')
        assert_equal(self.preprint.license.copyright_holders, ['Diane', 'Mr. Peanut Butter'])

        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.cc0_license._id,
            license_year='2015',
            copyright_holders=['Bojack Horseman', 'Princess Carolyn']
        )

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        self.preprint.license.reload()

        assert_equal(self.preprint.license.node_license, self.cc0_license)
        assert_equal(self.preprint.license.year, '2015')
        assert_equal(self.preprint.license.copyright_holders, ['Bojack Horseman', 'Princess Carolyn'])

    def test_update_preprint_license_without_required_year_in_payload(self):
        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.no_license._id,
            copyright_holders=['Rick', 'Morty']
        )

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'year must be specified for this license')

    def test_update_preprint_license_without_required_copyright_holders_in_payload_(self):
        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.no_license._id,
            license_year='1994'
        )

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'copyrightHolders must be specified for this license')

    def test_update_preprint_license_does_not_change_project_license(self):
        self.preprint.node.set_node_license(
            {
                'id': self.no_license.id,
                'year': '2015',
                'copyrightHolders': ['Simba', 'Mufasa']
            },
            auth=Auth(self.admin_contributor)
        )
        self.preprint.node.save()
        assert_equal(self.preprint.node.node_license.node_license, self.no_license)

        data = self.make_payload(
            node_id=self.preprint._id,
            license_id=self.cc0_license._id
        )

        res = self.make_request(self.url, data, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
        self.preprint.reload()

        assert_equal(self.preprint.license.node_license, self.cc0_license)
        assert_equal(self.preprint.node.node_license.node_license, self.no_license)
