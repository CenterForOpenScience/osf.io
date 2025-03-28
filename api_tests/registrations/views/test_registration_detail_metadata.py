import pytest

from api.base.settings.defaults import API_BASE
from osf.migrations import update_provider_auth_groups
from osf_tests.factories import (
    RegistrationFactory,
    RegistrationProviderFactory,
    AuthUserFactory,
)


@pytest.mark.django_db
class TestProviderSpecificMetadata():

    @pytest.fixture
    def registration_admin(self):
        return AuthUserFactory()

    @pytest.fixture
    def moderator(self):
        return AuthUserFactory()

    @pytest.fixture
    def provider(self, moderator):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.get_group('moderator').user_set.add(moderator)
        provider.additional_metadata_fields = [{'field_name': 'foo'}]
        provider.save()
        return provider

    @pytest.fixture
    def registration(self, provider, registration_admin):
        registration = RegistrationFactory(creator=registration_admin)
        registration.provider = provider
        registration.is_public = True
        registration.additional_metadata = {'foo': 'bar', 'fizz': 'buzz'}
        registration.save()
        return registration

    def get_registration_detail_url(self, registration):
        return f'/{API_BASE}registrations/{registration._id}/'

    def make_payload(self, registration, attributes):
        return {'data': {'id': registration._id, 'type': 'registrations', 'attributes': attributes}}

    @pytest.mark.parametrize(
        'supported_fields, expected_results',
        [
            ([], []),
            (['foo'], [{'field_name': 'foo', 'field_value': 'bar'}]),
            (['fizz'], [{'field_name': 'fizz', 'field_value': 'buzz'}]),
            (
                ['foo', 'fizz'],
                [
                    {'field_name': 'foo', 'field_value': 'bar'},
                    {'field_name': 'fizz', 'field_value': 'buzz'},
                ]
            ),
            (['baz'], [{'field_name': 'baz', 'field_value': ''}]),
        ]
    )
    def test_get_provider_metadata(self, supported_fields, expected_results, app, registration):
        # provider_specific_metadata should only surface
        # additional_metadata fields supported by the provider.
        provider = registration.provider
        provider.additional_metadata_fields = [{'field_name': field} for field in supported_fields]
        provider.save()

        resp = app.get(self.get_registration_detail_url(registration))
        assert resp.json['data']['attributes']['provider_specific_metadata'] == expected_results

    def test_get_provider_metadata_additional_metadata_fields_never_set(self, app):
        provider = RegistrationProviderFactory()
        registration = RegistrationFactory()
        registration.provider = provider
        registration.is_public = True
        registration.additional_metadata_fields = {'foo': 'bar'}
        registration.save()

        resp = app.get(self.get_registration_detail_url(registration))

        assert resp.json['data']['attributes']['provider_specific_metadata'] == []

    def test_get_provider_metadata_additional_metadata_never_set(self, app, provider):
        registration = RegistrationFactory()
        registration.provider = provider
        registration.is_public = True
        registration.save()

        resp = app.get(self.get_registration_detail_url(registration))

        expected_metadata = [{'field_name': 'foo', 'field_value': ''}]
        assert resp.json['data']['attributes']['provider_specific_metadata'] == expected_metadata

    def test_get_provider_metadata_no_addtional_fields_or_additional_metadata(self, app):
        provider = RegistrationProviderFactory()
        registration = RegistrationFactory()
        registration.provider = provider
        registration.is_public = True
        registration.save()

        resp = app.get(self.get_registration_detail_url(registration))

        assert resp.json['data']['attributes']['provider_specific_metadata'] == []

    def test_moderator_can_set_provider_metadata(self, app, registration, moderator):
        updated_metadata = [{'field_name': 'foo', 'field_value': 'buzz'}]
        payload = self.make_payload(registration, {'provider_specific_metadata': updated_metadata})

        resp = app.put_json_api(
            self.get_registration_detail_url(registration),
            payload,
            auth=moderator.auth
        )
        assert resp.status_code == 200

        registration.refresh_from_db()
        # Only previder-relevant metadata should be changed
        assert registration.additional_metadata == {'foo': 'buzz', 'fizz': 'buzz'}

        resp = app.get(self.get_registration_detail_url(registration))
        assert resp.json['data']['attributes']['provider_specific_metadata'] == updated_metadata

    def test_put_provider_specific_metadata_additional_metadata_is_uninitialized(self, app,
            provider, moderator):
        registration = RegistrationFactory()
        registration.provider = provider
        registration.save()
        assert not registration.additional_metadata

        payload = self.make_payload(
            registration,
            attributes={
                'provider_specific_metadata': [{'field_name': 'foo', 'field_value': 'bar'}]
            }
        )

        app.put_json_api(
            self.get_registration_detail_url(registration),
            payload,
            auth=moderator.auth
        )

        registration.refresh_from_db()
        assert registration.additional_metadata == {'foo': 'bar'}

    def test_put_unsupported_provider_metadata_is_400(self, app, registration, moderator):
        payload = self.make_payload(
            registration,
            attributes={
                'provider_specific_metadata': [{'field_name': 'fizz', 'field_value': 'bar'}]
            }
        )

        resp = app.put_json_api(
            self.get_registration_detail_url(registration),
            payload,
            auth=moderator.auth,
            expect_errors=True
        )
        assert resp.status_code == 400
        assert 'fizz' in resp.json['errors'][0]['detail']

    def test_put_no_supported_metadata_is_400(self, app, provider, registration, moderator):
        provider.additional_metadata_fields = None
        provider.save()
        payload = self.make_payload(
            registration,
            attributes={
                'provider_specific_metadata': [{'field_name': 'foo', 'field_value': 'buzz'}]
            }
        )

        resp = app.put_json_api(
            self.get_registration_detail_url(registration),
            payload,
            auth=moderator.auth,
            expect_errors=True
        )
        assert resp.status_code == 400
        assert 'detail' in resp.json['errors'][0]

    @pytest.mark.parametrize(
        'updated_fields, expected_results',
        [
            (
                {'foo': 'buzz'},
                [
                    {'field_name': 'foo', 'field_value': 'buzz'},
                    {'field_name': 'fizz', 'field_value': 'buzz'}
                ]
            ),
            (
                {'fizz': 'bar'},
                [
                    {'field_name': 'foo', 'field_value': 'bar'},
                    {'field_name': 'fizz', 'field_value': 'bar'},
                ]
            ),
            (
                {'foo': 'buzz', 'fizz': 'bar'},
                [
                    {'field_name': 'foo', 'field_value': 'buzz'},
                    {'field_name': 'fizz', 'field_value': 'bar'},
                ]
            ),
        ]
    )
    def test_put_with_multiple_provider_supported_fields(self, updated_fields, expected_results,
            app, registration, provider, moderator):

        provider.additional_metadata_fields.append({'field_name': 'fizz'})
        provider.save()

        updated_metadata = [
            {'field_name': key, 'field_value': val} for key, val in updated_fields.items()
        ]
        payload = self.make_payload(
            registration,
            attributes={'provider_specific_metadata': updated_metadata}
        )

        resp = app.put_json_api(
            self.get_registration_detail_url(registration),
            payload,
            auth=moderator.auth,
        )
        assert resp.status_code == 200

        registration.refresh_from_db()
        assert registration.provider_specific_metadata == expected_results

    def test_put_with_supported_and_unsupported_fields(self, app, registration, moderator):
        updated_metadata = [
            {'field_name': 'foo', 'field_value': 'buzz'},
            {'field_name': 'fizz', 'field_value': 'bar'}
        ]

        payload = self.make_payload(
            registration,
            attributes={'provider_specific_metadata': updated_metadata}
        )

        resp = app.put_json_api(
            self.get_registration_detail_url(registration),
            payload,
            auth=moderator.auth,
            expect_errors=True
        )
        assert resp.status_code == 400
        assert 'fizz' in resp.json['errors'][0]['detail']

    def test_admin_cannot_set_provider_metadata(self, app, registration, registration_admin):
        updated_metadata = [{'field_name': 'foo', 'field_value': 'buzz'}]
        payload = self.make_payload(
            registration,
            attributes={'provider_specific_metadata': updated_metadata}
        )

        resp = app.put_json_api(
            self.get_registration_detail_url(registration),
            payload,
            auth=registration_admin.auth,
            expect_errors=True
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize(
        'updated_field, updated_value',
        [
            ('public', True),
            ('category', 'instrumentation'),
            ('tags', ['this_should_have_failed']),
            ('description', 'access_denied'),
            ('custom_citation', 'By Mennen'),
            ('node_license', {'year': '2021', 'copyright_holders': ['COS']}),
            ('article_doi', '192.168.1.1'),
        ]
    )
    def test_moderator_cannot_set_other_fields(self, updated_field, updated_value, app,
            registration, moderator):
        payload = self.make_payload(registration, attributes={updated_field: updated_value})
        resp = app.put_json_api(
            self.get_registration_detail_url(registration),
            payload,
            auth=moderator.auth,
            expect_errors=True
        )

        assert resp.status_code == 403

    def test_moderator_admin_can_set_provider_fields_and_writeable_fields(self, app,
            provider, registration, registration_admin):
        provider.get_group('moderator').user_set.add(registration_admin)
        provider.save()
        updated_attributes = {
            'description': 'Setting all of the things',
            'provider_specific_metadata': [{'field_name': 'foo', 'field_value': 'baz'}],
        }
        payload = self.make_payload(registration, attributes=updated_attributes)
        resp = app.put_json_api(
            self.get_registration_detail_url(registration),
            payload,
            auth=registration_admin.auth
        )

        assert resp.status_code == 200

        registration.refresh_from_db()
        assert registration.description == 'Setting all of the things'
        assert registration.additional_metadata['foo'] == 'baz'
