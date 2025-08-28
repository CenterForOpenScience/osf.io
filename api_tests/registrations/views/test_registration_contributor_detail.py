from tests.base import ApiTestCase

from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
)
from api.base.settings.defaults import API_BASE
from tests.utils import capture_notifications


class TestRegistrationContributorDetailTestCase(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.creator = AuthUserFactory()
        self.read_contributor = AuthUserFactory()
        self.write_contributor = AuthUserFactory()
        self.public_project = ProjectFactory(
            title='Public Project',
            is_public=True,
            creator=self.creator
        )
        self.public_registration = RegistrationFactory(project=self.public_project, creator=self.creator)

        self.creator_id = f'{self.public_registration._id}-{self.creator._id}'
        self.read_contributor_id = f'{self.public_registration._id}-{self.read_contributor._id}'
        self.write_contributor_id = f'{self.public_registration._id}-{self.write_contributor._id}'

        self.public_url = f'/{API_BASE}registrations/{self.public_registration._id}/'
        self.add_contributor_url = f'/{API_BASE}registrations/{self.public_registration._id}/contributors/'
        self.edit_contributor_url = f'/{API_BASE}registrations/{self.public_registration._id}/contributors/'

    def form_contributors_create_payload(self, permission, contributor):
        return {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'permission': permission,
                    'bibliographic': True
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': contributor._id
                        }
                    }
                }
            }
        }

    def form_contributor_edit_payload(self, contributor, index):
        return {
            'data': {
                'id': f'{self.public_registration._id}-{contributor._id}',
                'attributes': {
                    'index': index
                },
                'relationships': {},
                'type': 'contributors'
            }
        }

    def test_initial_contributors_ordering_is_correct(self):
        read_payload = self.form_contributors_create_payload('read', self.read_contributor)
        write_payload = self.form_contributors_create_payload('write', self.write_contributor)
        with capture_notifications():
            self.app.post_json_api(
                self.add_contributor_url,
                read_payload,
                auth=self.creator.auth
            )
            self.app.post_json_api(
                self.add_contributor_url,
                write_payload,
                auth=self.creator.auth
            )

        contributors = self.app.get(self.add_contributor_url, auth=self.creator.auth)
        # shift by 1 because creator is the first contributor
        assert contributors.json['data'][1]['id'] == self.read_contributor_id
        assert contributors.json['data'][2]['id'] == self.write_contributor_id

    def test_contributors_reordering_works_correctly(self):
        read_payload = self.form_contributors_create_payload('read', self.read_contributor)
        write_payload = self.form_contributors_create_payload('write', self.write_contributor)
        with capture_notifications():
            self.app.post_json_api(
                self.add_contributor_url,
                read_payload,
                auth=self.creator.auth
            )
            self.app.post_json_api(
                self.add_contributor_url,
                write_payload,
                auth=self.creator.auth
            )

            self.app.patch_json_api(
                self.edit_contributor_url + f'{self.creator._id}/',
                self.form_contributor_edit_payload(self.creator, 2),
                auth=self.creator.auth
            )
            self.app.patch_json_api(
                self.edit_contributor_url + f'{self.read_contributor._id}/',
                self.form_contributor_edit_payload(self.read_contributor, 0),
                auth=self.creator.auth
            )

        contributors = self.app.get(self.add_contributor_url, auth=self.creator.auth)
        assert contributors.json['data'][0]['id'] == self.read_contributor_id
        assert contributors.json['data'][1]['id'] == self.write_contributor_id
        assert contributors.json['data'][2]['id'] == self.creator_id
