import pytest
from django.utils import timezone

from api.base.settings.defaults import API_BASE
from django.contrib.auth.models import Permission
from framework.auth.core import Auth
from osf.models import RegistrationSchema, RegistrationProvider
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
    AuthUserFactory,
    CollectionFactory,
    OSFGroupFactory,
    DraftRegistrationFactory,
)
from osf.utils import permissions
from website.project.metadata.utils import create_jsonschema_from_metaschema
from website import settings

OPEN_ENDED_SCHEMA_VERSION = 3
SCHEMA_VERSION = 2

@pytest.mark.django_db
class DraftRegistrationTestCase:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def group_mem(self):
        return AuthUserFactory()

    @pytest.fixture()
    def group(self, group_mem):
        return OSFGroupFactory(creator=group_mem)

    @pytest.fixture()
    def project_public(self, user, user_write_contrib, user_read_contrib, group, group_mem):
        project_public = ProjectFactory(is_public=True, creator=user)
        project_public.add_contributor(
            user_write_contrib,
            permissions=permissions.WRITE)
        project_public.add_contributor(
            user_read_contrib,
            permissions=permissions.READ)
        project_public.save()
        project_public.add_osf_group(group, permissions.ADMIN)
        project_public.add_tag('hello', Auth(user), save=True)
        return project_public

    @pytest.fixture()
    def metadata(self):
        def metadata(draft):
            test_metadata = {}
            json_schema = create_jsonschema_from_metaschema(
                draft.registration_schema.schema)

            for key, value in json_schema['properties'].items():
                response = 'Test response'
                items = value['properties']['value'].get('items')
                enum = value['properties']['value'].get('enum')
                if items:  # multiselect
                    response = [items['enum'][0]]
                elif enum:  # singleselect
                    response = enum[0]
                elif value['properties']['value'].get('properties'):
                    response = {'question': {'value': 'Test Response'}}

                test_metadata[key] = {'value': response}
            return test_metadata
        return metadata


@pytest.mark.django_db
class TestDraftRegistrationList(DraftRegistrationTestCase):

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(
            name='Open-Ended Registration',
            schema_version=OPEN_ENDED_SCHEMA_VERSION)

    @pytest.fixture()
    def draft_registration(self, user, project_public, schema):
        return DraftRegistrationFactory(
            initiator=user,
            registration_schema=schema,
            branched_from=project_public
        )

    @pytest.fixture()
    def url_draft_registrations(self, project_public):
        # Specifies version to test functionality when using DraftRegistrationLegacySerializer
        return '/{}nodes/{}/draft_registrations/?{}'.format(
            API_BASE, project_public._id, 'version=2.19')

    def test_admin_can_view_draft_list(
            self, app, user, draft_registration, project_public,
            schema, url_draft_registrations):
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1

        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']
        assert data[0]['id'] == draft_registration._id
        assert data[0]['attributes']['registration_metadata'] == {}

    def test_osf_group_with_admin_permissions_can_view(
            self, app, user, draft_registration, project_public,
            schema, url_draft_registrations):
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        project_public.add_osf_group(group, permissions.ADMIN)
        res = app.get(url_draft_registrations, auth=group_mem.auth, expect_errors=True)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']

    def test_cannot_view_draft_list(
            self, app, user_write_contrib, project_public,
            user_read_contrib, user_non_contrib,
            url_draft_registrations, group, group_mem):

        # test_read_only_contributor_cannot_view_draft_list
        res = app.get(
            url_draft_registrations,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_read_write_contributor_cannot_view_draft_list
        res = app.get(
            url_draft_registrations,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_logged_in_non_contributor_cannot_view_draft_list
        res = app.get(
            url_draft_registrations,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_unauthenticated_user_cannot_view_draft_list
        res = app.get(url_draft_registrations, expect_errors=True)
        assert res.status_code == 401

    #   test_osf_group_with_read_permissions
        project_public.remove_osf_group(group)
        project_public.add_osf_group(group, permissions.READ)
        res = app.get(url_draft_registrations, auth=group_mem.auth, expect_errors=True)
        assert res.status_code == 403

    def test_deleted_draft_registration_does_not_show_up_in_draft_list(
            self, app, user, draft_registration, url_draft_registrations):
        draft_registration.deleted = timezone.now()
        draft_registration.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 0

    def test_draft_with_registered_node_does_not_show_up_in_draft_list(
            self, app, user, project_public, draft_registration, url_draft_registrations):
        reg = RegistrationFactory(project=project_public, draft_registration=draft_registration)
        draft_registration.registered_node = reg
        draft_registration.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 0

    def test_draft_with_deleted_registered_node_shows_up_in_draft_list(
            self, app, user, project_public,
            draft_registration, schema,
            url_draft_registrations):
        reg = RegistrationFactory(project=project_public, draft_registration=draft_registration)
        draft_registration.registered_node = reg
        draft_registration.save()
        reg.is_deleted = True
        reg.save()
        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1
        assert schema._id in data[0]['relationships']['registration_schema']['links']['related']['href']
        assert data[0]['id'] == draft_registration._id
        assert data[0]['attributes']['registration_metadata'] == {}

    def test_draft_registration_serializer_usage(self, app, user, project_public, draft_registration):
        # Tests the usage of DraftRegistrationDetailSerializer for version 2.20
        url_draft_registrations = '/{}nodes/{}/draft_registrations/?{}'.format(
            API_BASE, project_public._id, 'version=2.20')

        res = app.get(url_draft_registrations, auth=user.auth)
        assert res.status_code == 200
        data = res.json['data']
        assert len(data) == 1

        # Set of fields that DraftRegistrationLegacySerializer does not provide
        assert data[0]['attributes']['title']
        assert data[0]['attributes']['description']
        assert data[0]['relationships']['affiliated_institutions']


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestDraftRegistrationCreate(DraftRegistrationTestCase):

    @pytest.fixture()
    def provider(self):
        return RegistrationProvider.get_default()

    @pytest.fixture()
    def non_default_provider(self, metaschema_open_ended):
        non_default_provider = RegistrationProviderFactory()
        non_default_provider.schemas.add(metaschema_open_ended)
        non_default_provider.save()
        return non_default_provider

    @pytest.fixture()
    def metaschema_open_ended(self):
        return RegistrationSchema.objects.get(
            name='Open-Ended Registration',
            schema_version=OPEN_ENDED_SCHEMA_VERSION)

    @pytest.fixture()
    def payload(self, metaschema_open_ended, provider):
        return {
            'data': {
                'type': 'draft_registrations',
                'attributes': {},
                'relationships': {
                    'registration_schema': {
                        'data': {
                            'type': 'registration_schema',
                            'id': metaschema_open_ended._id
                        }
                    },
                    'provider': {
                        'data': {
                            'type': 'registration-providers',
                            'id': provider._id,
                        }
                    }
                }
            }
        }

    @pytest.fixture()
    def payload_with_non_default_provider(self, metaschema_open_ended, non_default_provider):
        return {
            'data': {
                'type': 'draft_registrations',
                'attributes': {},
                'relationships': {
                    'registration_schema': {
                        'data': {
                            'type': 'registration_schema',
                            'id': metaschema_open_ended._id
                        }
                    },
                    'provider': {
                        'data': {
                            'type': 'registration-providers',
                            'id': non_default_provider._id,
                        }
                    }
                }
            }
        }

    @pytest.fixture()
    def url_draft_registrations(self, project_public):
        return '/{}nodes/{}/draft_registrations/?{}'.format(
            API_BASE, project_public._id, 'version=2.19')

    def test_type_is_draft_registrations(
            self, app, user, metaschema_open_ended,
            url_draft_registrations):
        draft_data = {
            'data': {
                'type': 'nodes',
                'attributes': {},
                'relationships': {
                    'registration_schema': {
                        'data': {
                            'type': 'registration_schema',
                            'id': metaschema_open_ended._id
                        }

                    }
                }
            }
        }
        res = app.post_json_api(
            url_draft_registrations,
            draft_data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409

    def test_admin_can_create_draft(
            self, app, user, project_public, url_draft_registrations,
            payload, metaschema_open_ended):
        url = '{}&embed=branched_from&embed=initiator'.format(url_draft_registrations)
        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        data = res.json['data']
        assert metaschema_open_ended._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['attributes']['registration_metadata'] == {}
        assert f'{settings.API_DOMAIN}v2/providers/registrations/{RegistrationProvider.default__id}/' in \
               data['relationships']['provider']['links']['related']['href']
        assert data['embeds']['branched_from']['data']['id'] == project_public._id
        assert data['embeds']['initiator']['data']['id'] == user._id

    def test_cannot_create_draft(
            self, app, user_write_contrib,
            user_read_contrib, user_non_contrib,
            project_public, payload, group,
            url_draft_registrations, group_mem):

        #   test_write_only_contributor_cannot_create_draft
        assert user_write_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_read_only_contributor_cannot_create_draft
        assert user_read_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_non_authenticated_user_cannot_create_draft
        res = app.post_json_api(
            url_draft_registrations,
            payload, expect_errors=True)
        assert res.status_code == 401

    #   test_logged_in_non_contributor_cannot_create_draft
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_group_admin_cannot_create_draft
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_group_write_contrib_cannot_create_draft
        project_public.remove_osf_group(group)
        project_public.add_osf_group(group, permissions.WRITE)
        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_reviewer_cannot_create_draft_registration
        user = AuthUserFactory()
        administer_permission = Permission.objects.get(
            codename='administer_prereg')
        user.user_permissions.add(administer_permission)
        user.save()

        assert user_read_contrib in project_public.contributors.all()
        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 403

    def test_schema_validation(
            self, app, user, provider, non_default_provider, payload, payload_with_non_default_provider, url_draft_registrations):
        # Schema validation for a default provider without defined schemas with any schema is tested by `test_admin_can_create_draft`
        # Schema validation for a non-default provider with the correct schema is tested by `test_create_draft_with_provider`

        # Default provider with defined schemas does not accept everything
        schema = RegistrationSchema.objects.get(
            name='Prereg Challenge',
            schema_version=SCHEMA_VERSION)
        provider.schemas.add(schema)
        provider.save()

        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

        payload['data']['relationships']['registration_schema']['data']['id'] = schema._id

        res = app.post_json_api(
            url_draft_registrations,
            payload,
            auth=user.auth)
        assert res.status_code == 201

        # Non-Default provider does not accept everything
        payload_with_non_default_provider['data']['relationships']['registration_schema']['data']['id'] = schema._id
        res = app.post_json_api(
            url_draft_registrations,
            payload_with_non_default_provider,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

    def test_registration_supplement_errors(
            self, app, user, provider, url_draft_registrations):

        #   test_registration_supplement_not_found
        draft_data = {
            'data': {
                'type': 'draft_registrations',
                'attributes': {},
                'relationships': {
                    'registration_schema': {
                        'data': {
                            'type': 'registration_schema',
                            'id': 'Invalid schema'
                        }
                    },
                    'provider': {
                        'data': {
                            'type': 'registration-providers',
                            'id': provider._id,
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_draft_registrations,
            draft_data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    #   test_registration_supplement_must_be_active_metaschema
        schema = RegistrationSchema.objects.get(
            name='Election Research Preacceptance Competition', active=False)
        draft_data = {
            'data': {
                'type': 'draft_registrations',
                'attributes': {},
                'relationships': {
                    'registration_schema': {
                        'data': {
                            'type': 'registration_schema',
                            'id': schema._id
                        }
                    },
                    'provider': {
                        'data': {
                            'type': 'registration-providers',
                            'id': provider._id,
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_draft_registrations,
            draft_data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Registration supplement must be an active schema.'

    #   test_registration_supplement_must_be_active
        schema = RegistrationSchema.objects.get(
            name='Election Research Preacceptance Competition', schema_version=2)
        draft_data = {
            'data': {
                'type': 'draft_registrations',
                'attributes': {},
                'relationships': {
                    'registration_schema': {
                        'data': {
                            'type': 'registration_schema',
                            'id': schema._id
                        }
                    },
                    'provider': {
                        'data': {
                            'type': 'registration-providers',
                            'id': provider._id,
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url_draft_registrations,
            draft_data, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Registration supplement must be an active schema.'

    def test_cannot_create_draft_errors(
            self, app, user, project_public, payload):

        #   test_cannot_create_draft_from_a_registration
        registration = RegistrationFactory(
            project=project_public, creator=user)
        url = '/{}nodes/{}/draft_registrations/'.format(
            API_BASE, registration._id)
        res = app.post_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    #   test_cannot_create_draft_from_deleted_node
        project = ProjectFactory(is_public=True, creator=user)
        project.is_deleted = True
        project.save()
        url_project = '/{}nodes/{}/draft_registrations/'.format(
            API_BASE, project._id)
        res = app.post_json_api(
            url_project, payload,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 410
        assert res.json['errors'][0]['detail'] == 'The requested node is no longer available.'

    #   test_cannot_create_draft_from_collection
        collection = CollectionFactory(creator=user)
        url = '/{}nodes/{}/draft_registrations/'.format(
            API_BASE, collection._id)
        res = app.post_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_required_metaschema_questions_not_required_on_post(
            self, app, user, provider, project_public, metadata, url_draft_registrations):
        prereg_schema = RegistrationSchema.objects.get(
            name='Prereg Challenge',
            schema_version=SCHEMA_VERSION)

        prereg_draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=prereg_schema,
            branched_from=project_public
        )

        url = '{}&embed=initiator&embed=branched_from'.format(url_draft_registrations)

        registration_metadata = metadata(prereg_draft_registration)
        del registration_metadata['q1']
        prereg_draft_registration.registration_metadata = registration_metadata
        prereg_draft_registration.save()

        payload = {
            'data': {
                'type': 'draft_registrations',
                'attributes': {
                    'registration_metadata': registration_metadata
                },
                'relationships': {
                    'branched_from': {
                        'data': {
                            'type': 'nodes',
                            'id': project_public._id,
                        }
                    },
                    'registration_schema': {
                        'data': {
                            'type': 'registration_schema',
                            'id': prereg_schema._id
                        }
                    },
                    'provider': {
                        'data': {
                            'type': 'registration-providers',
                            'id': provider._id,
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 201
        data = res.json['data']
        assert prereg_schema._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['embeds']['branched_from']['data']['id'] == project_public._id
        assert data['embeds']['initiator']['data']['id'] == user._id

    def test_required_registration_responses_questions_not_required_on_post(
            self, app, user, provider, project_public):
        prereg_schema = RegistrationSchema.objects.get(
            name='Prereg Challenge',
            schema_version=SCHEMA_VERSION)

        prereg_draft_registration = DraftRegistrationFactory(
            initiator=user,
            registration_schema=prereg_schema,
            branched_from=project_public
        )

        url = '/{}nodes/{}/draft_registrations/?embed=initiator&embed=branched_from'.format(
            API_BASE, project_public._id)

        registration_responses = {'q1': 'answer to the question'}
        prereg_draft_registration.registration_metadata = {}
        prereg_draft_registration.save()

        payload = {
            'data': {
                'type': 'draft_registrations',
                'attributes': {
                    'registration_responses': registration_responses
                },
                'relationships': {
                    'registration_schema': {
                        'data': {
                            'type': 'registration_schema',
                            'id': prereg_schema._id
                        }
                    },
                    'provider': {
                        'data': {
                            'type': 'registration-providers',
                            'id': provider._id,
                        }
                    }
                }
            }
        }
        res = app.post_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 201
        data = res.json['data']
        assert res.json['data']['attributes']['registration_metadata']['q1']['value'] == registration_responses['q1']
        assert res.json['data']['attributes']['registration_responses']['q1'] == registration_responses['q1']
        assert prereg_schema._id in data['relationships']['registration_schema']['links']['related']['href']
        assert data['embeds']['branched_from']['data']['id'] == project_public._id
        assert data['embeds']['initiator']['data']['id'] == user._id

    def test_registration_supplement_must_be_supplied(
            self, app, user, url_draft_registrations):
        draft_data = {
            'data': {
                'type': 'draft_registrations',
                'attributes': {
                }
            }
        }
        res = app.post_json_api(
            url_draft_registrations,
            draft_data, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'This field is required.'
        assert errors['source']['pointer'] == '/data/relationships/registration_schema'

    def test_cannot_supply_both_registration_metadata_and_registration_responses(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata'] = {'summary': 'Registration data'}
        payload['data']['attributes']['registration_responses'] = {'summary': 'Registration data'}

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert 'Please use `registration_responses` as `registration_metadata` will be deprecated in the future.' in errors['detail']

    def test_supply_registration_responses_on_creation(
            self, app, user, payload, url_draft_registrations):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

        payload['data']['relationships']['registration_schema']['data']['id'] = schema._id
        payload['data']['attributes']['registration_responses'] = {
            'looked': 'Yes',
            'datacompletion': 'No, data collection has not begun',
            'comments': ''
        }
        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)

        attributes = res.json['data']['attributes']
        assert attributes['registration_responses'] == {
            'looked': 'Yes',
            'datacompletion': 'No, data collection has not begun',
            'comments': ''
        }
        assert attributes['registration_metadata'] == {
            'looked': {
                'comments': [],
                'value': 'Yes',
                'extra': []
            },
            'datacompletion': {
                'comments': [],
                'value': 'No, data collection has not begun',
                'extra': []
            },
            'comments': {
                'comments': [],
                'value': '',
                'extra': []
            }
        }

    def test_registration_metadata_must_be_a_dictionary(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_metadata'] = 'Registration data'

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['source']['pointer'] == '/data/attributes/registration_metadata'
        assert errors['detail'] == 'Expected a dictionary of items but got type "str".'

    def test_registration_metadata_question_values_must_be_dictionaries(
            self, app, user, payload, url_draft_registrations):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)
        payload['data']['relationships']['registration_schema']['data']['id'] = schema._id
        payload['data']['attributes']['registration_metadata'] = {}
        payload['data']['attributes']['registration_metadata']['datacompletion'] = 'No, data collection has not begun'

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration your response to the \'Data collection status\' field' \
                                   ' is invalid, your response must be one of the provided options.'

    def test_registration_metadata_question_keys_must_be_value(
            self, app, user, payload, url_draft_registrations):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

        payload['data']['relationships']['registration_schema']['data']['id'] = schema._id
        payload['data']['attributes']['registration_metadata'] = {}
        payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            'incorrect_key': 'No, data collection has not begun'}

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration your response to the \'Data collection status\' ' \
                                   'field is invalid, your response must be one of the provided options.'

    def test_question_in_registration_metadata_must_be_in_schema(
            self, app, user, payload, url_draft_registrations):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

        payload['data']['relationships']['registration_schema']['data']['id'] = schema._id
        payload['data']['attributes']['registration_metadata'] = {}
        payload['data']['attributes']['registration_metadata']['q11'] = {
            'value': 'No, data collection has not begun'
        }

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration the \'datacompletion\' field is extraneous and not' \
                                   ' permitted in your response.'

    def test_multiple_choice_question_value_must_match_value_in_schema(
            self, app, user, payload, url_draft_registrations):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

        payload['data']['relationships']['registration_schema']['data']['id'] = schema._id
        payload['data']['attributes']['registration_metadata'] = {}
        payload['data']['attributes']['registration_metadata']['datacompletion'] = {
            'value': 'Nope, data collection has not begun'}

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration your response to the \'Data collection status\'' \
                                   ' field is invalid, your response must be one of the provided options.'

    def test_registration_responses_must_be_a_dictionary(
            self, app, user, payload, url_draft_registrations):
        payload['data']['attributes']['registration_responses'] = 'Registration data'

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['source']['pointer'] == '/data/attributes/registration_responses'
        assert errors['detail'] == 'Expected a dictionary of items but got type "str".'

    def test_registration_responses_question_values_must_not_be_dictionaries(
            self, app, user, payload, url_draft_registrations):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)
        payload['data']['relationships']['registration_schema']['data']['id'] = schema._id
        payload['data']['attributes']['registration_responses'] = {}
        payload['data']['attributes']['registration_responses']['datacompletion'] = {'value': 'No, data collection has not begun'}

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration, your response to the \'Data collection status\' field' \
                                   ' is invalid, your response must be one of the provided options.'

    def test_question_in_registration_responses_must_be_in_schema(
            self, app, user, payload, url_draft_registrations):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

        payload['data']['relationships']['registration_schema']['data']['id'] = schema._id
        payload['data']['attributes']['registration_responses'] = {}
        payload['data']['attributes']['registration_responses']['q11'] = 'No, data collection has not begun'

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'Additional properties are not allowed (\'q11\' was unexpected)'

    def test_registration_responses_multiple_choice_question_value_must_match_value_in_schema(
            self, app, user, payload, url_draft_registrations):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=SCHEMA_VERSION)

        payload['data']['relationships']['registration_schema']['data']['id'] = schema._id
        payload['data']['attributes']['registration_responses'] = {}
        payload['data']['attributes']['registration_responses']['datacompletion'] = 'Nope, data collection has not begun'

        res = app.post_json_api(
            url_draft_registrations,
            payload, auth=user.auth,
            expect_errors=True)
        errors = res.json['errors'][0]
        assert res.status_code == 400
        assert errors['detail'] == 'For your registration, your response to the \'Data collection status\'' \
                                   ' field is invalid, your response must be one of the provided options.'
