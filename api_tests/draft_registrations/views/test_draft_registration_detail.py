import pytest

from django.contrib.auth.models import Permission
from api.base.settings.defaults import API_BASE
from api_tests.nodes.views.test_node_draft_registration_detail import (
    TestDraftRegistrationDetail,
    TestDraftRegistrationUpdate,
    TestDraftRegistrationPatch,
    TestDraftRegistrationDelete,
    TestDraftPreregChallengeRegistrationMetadataValidation
)
from osf.models import DraftNode, Node, NodeLicense, RegistrationSchema
from osf.utils.permissions import ADMIN, READ, WRITE
from osf_tests.factories import (
    DraftRegistrationFactory,
    AuthUserFactory,
    InstitutionFactory,
    SubjectFactory,
    ProjectFactory,
)


@pytest.mark.django_db
class TestDraftRegistrationDetailEndpoint(TestDraftRegistrationDetail):
    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        return '/{}draft_registrations/{}/'.format(
            API_BASE, draft_registration._id)

    # Overrides TestDraftRegistrationDetail
    def test_admin_group_member_can_view(self, app, user, draft_registration, project_public,
            schema, url_draft_registrations, group_mem):

        res = app.get(url_draft_registrations, auth=group_mem.auth, expect_errors=True)
        assert res.status_code == 403

    def test_can_view_draft(
            self, app, user_write_contrib, project_public,
            user_read_contrib, user_non_contrib,
            url_draft_registrations, group, group_mem):

        #   test_read_only_contributor_can_view_draft
        res = app.get(
            url_draft_registrations,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 200

        #   test_read_write_contributor_can_view_draft
        res = app.get(
            url_draft_registrations,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 200

    def test_cannot_view_draft(
            self, app, project_public,
            user_non_contrib, url_draft_registrations):

        #   test_logged_in_non_contributor_cannot_view_draft
        res = app.get(
            url_draft_registrations,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

        #   test_unauthenticated_user_cannot_view_draft
        res = app.get(url_draft_registrations, expect_errors=True)
        assert res.status_code == 401

    def test_detail_view_returns_editable_fields(self, app, user, draft_registration,
            url_draft_registrations, project_public):

        res = app.get(url_draft_registrations, auth=user.auth, expect_errors=True)
        attributes = res.json['data']['attributes']

        assert attributes['title'] == project_public.title
        assert attributes['description'] == project_public.description
        assert attributes['category'] == project_public.category

        res.json['data']['links']['self'] == url_draft_registrations

        relationships = res.json['data']['relationships']
        assert Node.load(relationships['branched_from']['data']['id']) == draft_registration.branched_from

        assert 'affiliated_institutions' in relationships
        assert 'subjects' in relationships
        assert 'contributors' in relationships

    def test_detail_view_returns_editable_fields_no_specified_node(self, app, user):

        draft_registration = DraftRegistrationFactory(initiator=user, branched_from=None)
        url = '/{}draft_registrations/{}/'.format(
            API_BASE, draft_registration._id)

        res = app.get(url, auth=user.auth, expect_errors=True)
        attributes = res.json['data']['attributes']

        assert attributes['title'] == 'Untitled'
        assert attributes['description'] == ''
        assert attributes['category'] == ''
        assert attributes['node_license'] is None

        res.json['data']['links']['self'] == url
        relationships = res.json['data']['relationships']

        assert 'affiliated_institutions' in relationships
        assert 'subjects' in relationships
        assert 'contributors' in relationships

        draft_node_link = relationships['branched_from']['links']['related']['href']
        res = app.get(draft_node_link, auth=user.auth)
        assert DraftNode.load(res.json['data']['id']) == draft_registration.branched_from

    def test_draft_registration_perms_checked_on_draft_not_node(self, app, user, project_public,
            draft_registration, url_draft_registrations):

        # Admin on node and draft
        assert project_public.has_permission(user, ADMIN) is True
        assert draft_registration.has_permission(user, ADMIN) is True
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200

        # Admin on node but not draft
        node_admin = AuthUserFactory()
        project_public.add_contributor(node_admin, ADMIN)
        assert project_public.has_permission(node_admin, ADMIN) is True
        assert draft_registration.has_permission(node_admin, ADMIN) is False
        res = app.get(url_draft_registrations, auth=node_admin.auth)
        assert res.status_code == 200

        # Admin on draft but not node
        draft_admin = AuthUserFactory()
        draft_registration.add_contributor(draft_admin, ADMIN)
        assert project_public.has_permission(draft_admin, ADMIN) is False
        assert draft_registration.has_permission(draft_admin, ADMIN) is True
        res = app.get(url_draft_registrations, auth=draft_admin.auth, expect_errors=True)
        assert res.status_code == 403

    # Overwrites TestDraftRegistrationDetail
    def test_can_view_after_added(
            self, app, schema, draft_registration, url_draft_registrations):
        # Draft Registration permissions are based on the branched from node

        user = AuthUserFactory()
        project = draft_registration.branched_from
        project.add_contributor(user, ADMIN)
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200

    # Overrides TestDraftRegistrationDetail
    def test_reviewer_can_see_draft_registration(
            self, app, schema, draft_registration, url_draft_registrations):
        user = AuthUserFactory()
        administer_permission = Permission.objects.get(
            codename='administer_prereg')
        user.user_permissions.add(administer_permission)
        user.save()
        res = app.get(url_draft_registrations, auth=user.auth, expect_errors=True)
        # New workflows aren't accommodating old prereg challenge
        assert res.status_code == 403


class TestUpdateEditableFieldsTestCase:
    @pytest.fixture()
    def license(self):
        return NodeLicense.objects.get(license_id='GPL3')

    @pytest.fixture()
    def copyright_holders(self):
        return ['Richard Stallman']

    @pytest.fixture()
    def year(self):
        return '2019'

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def title(self):
        return 'California shrub oak'

    @pytest.fixture()
    def description(self):
        return 'Quercus berberidifolia'

    @pytest.fixture()
    def category(self):
        return 'software'

    @pytest.fixture()
    def editable_fields_payload(self, draft_registration, license, copyright_holders,
            year, institution_one, title, description, category, subject,):
        return {
            'data': {
                'id': draft_registration._id,
                'type': 'draft_registrations',
                'attributes': {
                    'title': title,
                    'description': description,
                    'category': category,
                    'node_license': {
                        'year': year,
                        'copyright_holders': copyright_holders
                    },
                    'tags': ['oak', 'tree'],
                    'registration_metadata': {
                        'datacompletion': {
                            'value': 'No, data collection has not begun'
                        },
                        'looked': {
                            'value': 'No'
                        },
                        'comments': {
                            'value': 'This is my first registration.'
                        }
                    }
                },
                'relationships': {
                    'license': {
                        'data': {
                            'type': 'licenses',
                            'id': license._id
                        }
                    },
                    'affiliated_institutions': {
                        'data': [
                            {'type': 'institutions', 'id': institution_one._id}
                        ]
                    },
                    'subjects': {
                        'data': [
                            {'id': subject._id, 'type': 'subjects'},
                        ]
                    }
                }
            }
        }


@pytest.mark.django_db
class TestDraftRegistrationUpdateWithNode(TestDraftRegistrationUpdate, TestUpdateEditableFieldsTestCase):
    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        return '/{}draft_registrations/{}/'.format(
            API_BASE, draft_registration._id)

    @pytest.fixture()
    def draft_registration(self, user, user_read_contrib, user_write_contrib, project_public, schema):
        draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=None
        )
        draft_registration.add_contributor(
            user_write_contrib,
            permissions=WRITE)
        draft_registration.add_contributor(
            user_read_contrib,
            permissions=READ)
        draft_registration.save()
        return draft_registration

    @pytest.fixture()
    def schema_open_ended(self):
        return RegistrationSchema.objects.get(
            name='Open-Ended Registration',
            schema_version=3)

    @pytest.fixture
    def draft_registration_open_ended(self, user, schema_open_ended):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema_open_ended,
            branched_from=None
        )

    @pytest.fixture()
    def url_draft_registration_open_ended(self, draft_registration_open_ended):
        return f'/{API_BASE}draft_registrations/{draft_registration_open_ended._id}/'

    @pytest.fixture()
    def upload_payload(self, draft_registration_open_ended):
        return {
            'data': {
                'id': draft_registration_open_ended._id,
                'attributes': {
                    'registration_responses': {
                        'uploader': [{
                            'file_id': '5eda89dfc00e6f0570715e5b',
                            'file_name': 'Cafe&LunchMenu.pdf',
                            'file_hashes': {
                                'sha256': '2161a32cfe1cbbfbd73aa541fdcb8c407523a8828bfd7a031362e1763a74e8ad'
                            },
                            'file_urls': {
                                'html': f'{API_BASE}/etch4/files/osfstorage/5eda89dfc00e6f0570715e5b',
                                'download': f'{API_BASE}/download/b56ve/'
                            }
                        }]
                    }
                },
                'relationships': {},
                'type': 'draft_registrations'
            }
        }

    def test_update_editable_fields(self, app, url_draft_registrations, draft_registration, license, copyright_holders,
            year, institution_one, user, title, description, category, subject, editable_fields_payload):
        user.affiliated_institutions.add(institution_one)

        res = app.put_json_api(
            url_draft_registrations, editable_fields_payload,
            auth=user.auth)
        assert res.status_code == 200
        attributes = res.json['data']['attributes']

        assert attributes['title'] == title
        assert attributes['description'] == description
        assert attributes['category'] == category
        assert attributes['node_license']['year'] == year
        assert attributes['node_license']['copyright_holders'] == copyright_holders
        assert set(attributes['tags']) == set(['oak', 'tree'])
        assert attributes['registration_metadata'] == {
            'datacompletion': {
                'value': 'No, data collection has not begun'
            },
            'looked': {
                'value': 'No'
            },
            'comments': {
                'value': 'This is my first registration.'
            }
        }

        relationships = res.json['data']['relationships']
        assert relationships['license']['data']['id'] == license._id

        subjects = draft_registration.subjects.values_list('id', flat=True)
        assert len(subjects) == 1
        assert subjects[0] == subject.id
        assert 'draft_registrations/{}/subjects'.format(draft_registration._id) in relationships['subjects']['links']['related']['href']
        assert 'draft_registrations/{}/relationships/subjects'.format(draft_registration._id) in relationships['subjects']['links']['self']['href']

        affiliated_institutions = draft_registration.affiliated_institutions.values_list('id', flat=True)
        assert len(affiliated_institutions) == 1
        assert affiliated_institutions[0] == institution_one.id
        assert 'draft_registrations/{}/institutions'.format(draft_registration._id) in relationships['affiliated_institutions']['links']['related']['href']
        assert 'draft_registrations/{}/relationships/institutions'.format(draft_registration._id) in relationships['affiliated_institutions']['links']['self']['href']

        assert 'draft_registrations/{}/contributors'.format(draft_registration._id) in relationships['contributors']['links']['related']['href']

    def test_update_upload(self, app, url_draft_registration_open_ended, draft_registration_open_ended, upload_payload, user):
        res = app.patch_json_api(
            url_draft_registration_open_ended,
            upload_payload,
            auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['registration_responses']['uploader'][0]['file_name'] == 'Cafe&LunchMenu.pdf'

    def test_registration_metadata_must_be_supplied(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes'] = {}

        res = app.put_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        # Override - not required
        assert res.status_code == 200

    def test_editable_title(
            self, app, user, editable_fields_payload, url_draft_registrations, institution_one):
        # User must have permissions on the institution included in the editable_fields_payload
        user.affiliated_institutions.add(institution_one)

        # test blank title - should be allowed
        editable_fields_payload['data']['attributes']['title'] = ''
        res = app.put_json_api(
            url_draft_registrations, editable_fields_payload,
            auth=user.auth)
        assert res.status_code == 200

        # test null title
        editable_fields_payload['data']['attributes']['title'] = None
        res = app.put_json_api(
            url_draft_registrations, editable_fields_payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    def test_invalid_editable_category(
            self, app, user, editable_fields_payload, url_draft_registrations):

        # test blank title
        editable_fields_payload['data']['attributes']['category'] = 'Not a category'
        res = app.put_json_api(
            url_draft_registrations, editable_fields_payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"Not a category" is not a valid choice.'

    def test_cannot_edit_node(self, app, user, url_draft_registrations, draft_registration):
        node = ProjectFactory(creator=user)
        branched_from = draft_registration.branched_from
        payload = {
            'data': {
                'id': draft_registration._id,
                'type': 'draft_registrations',
                'relationships': {
                    'branched_from': {
                        'data': {
                            'id': node._id,
                            'type': 'nodes'
                        }
                    }
                }
            }
        }
        res = app.put_json_api(
            url_draft_registrations, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        draft_registration.reload()

        assert draft_registration.branched_from == branched_from
        assert draft_registration.branched_from != node

    def test_write_contributor_can_update_draft(
            self, app, user_write_contrib, schema, project_public,
            payload, url_draft_registrations):
        res = app.put_json_api(
            url_draft_registrations,
            payload,
            auth=user_write_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert schema._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['attributes']['registration_metadata'] == payload['data']['attributes']['registration_metadata']
        # A write to registration_metadata, also updates registration_responses
        assert data['attributes']['registration_responses'] == {
            'datacompletion': 'No, data collection has not begun',
            'looked': 'No',
            'comments': 'This is my first registration.'
        }

    def test_write_contributor_can_update_draft_no_title(
            self, app, user_write_contrib, schema, project_public,
            payload, url_draft_registrations):

        payload['data']['attributes']['title'] = ''
        res = app.put_json_api(
            url_draft_registrations,
            payload,
            auth=user_write_contrib.auth
        )

        assert res.status_code == 200
        data = res.json['data']
        assert schema._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['attributes']['registration_metadata'] == payload['data']['attributes']['registration_metadata']
        # A write to registration_metadata, also updates registration_responses
        assert data['attributes']['registration_responses'] == {
            'datacompletion': 'No, data collection has not begun',
            'looked': 'No',
            'comments': 'This is my first registration.'
        }


@pytest.mark.django_db
class TestDraftRegistrationUpdateWithDraftNode(TestDraftRegistrationUpdate):
    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        return '/{}draft_registrations/{}/'.format(
            API_BASE, draft_registration._id)

    @pytest.fixture()
    def draft_registration(self, user, user_read_contrib, user_write_contrib, project_public, schema):
        draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=None
        )
        draft_registration.add_contributor(
            user_write_contrib,
            permissions=WRITE)
        draft_registration.add_contributor(
            user_read_contrib,
            permissions=READ)
        draft_registration.save()
        return draft_registration

    def test_write_contributor_can_update_draft(
            self, app, user_write_contrib, schema, project_public,
            payload, url_draft_registrations):
        res = app.put_json_api(
            url_draft_registrations,
            payload,
            auth=user_write_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert schema._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['attributes']['registration_metadata'] == payload['data']['attributes']['registration_metadata']
        # A write to registration_metadata, also updates registration_responses
        assert data['attributes']['registration_responses'] == {
            'datacompletion': 'No, data collection has not begun',
            'looked': 'No',
            'comments': 'This is my first registration.'
        }


class TestDraftRegistrationPatchNew(TestDraftRegistrationPatch):
    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        # Overrides TestDraftRegistrationPatch
        return '/{}draft_registrations/{}/'.format(
            API_BASE, draft_registration._id)

    @pytest.fixture()
    def draft_registration(self, user, user_read_contrib, user_write_contrib, project_public, schema):
        draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=None
        )
        draft_registration.add_contributor(
            user_write_contrib,
            permissions=WRITE)
        draft_registration.add_contributor(
            user_read_contrib,
            permissions=READ)
        draft_registration.save()
        return draft_registration

    def test_write_contributor_can_update_draft(
            self, app, user_write_contrib, schema, payload,
            url_draft_registrations):
        res = app.patch_json_api(
            url_draft_registrations,
            payload,
            auth=user_write_contrib.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert schema._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['attributes']['registration_metadata'] == payload['data']['attributes']['registration_metadata']


class TestDraftRegistrationDelete(TestDraftRegistrationDelete):
    @pytest.fixture()
    def url_draft_registrations(self, project_public, draft_registration):
        # Overrides TestDraftRegistrationDelete
        return '/{}draft_registrations/{}/'.format(
            API_BASE, draft_registration._id)


class TestDraftPreregChallengeRegistrationMetadataValidationNew(TestDraftPreregChallengeRegistrationMetadataValidation):
    @pytest.fixture()
    def url_draft_registrations(
            self, project_public,
            draft_registration_prereg):
        return '/{}draft_registrations/{}/'.format(
            API_BASE, draft_registration_prereg._id)
