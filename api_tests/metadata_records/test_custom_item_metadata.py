import pytest

from django.db import transaction

from api.base.settings.defaults import API_BASE
from osf.models import GuidMetadataRecord
from osf.utils import permissions
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    PreprintFactory,
)


def make_url(guid):
    base_url = f'/{API_BASE}custom_item_metadata_records/'
    if guid is None:
        return base_url
    if hasattr(guid, 'guid'):
        guid = guid.guid
    return f'{base_url}osfio:{guid._id}/'


def make_payload(guid, **attributes):
    if hasattr(guid, 'guid'):
        guid = guid.guid
    return {
        'data': {
            'id': guid._id,
            'type': 'custom-item-metadata-records',
            'attributes': attributes,
        }
    }


class TestCustomItemMetadataRecordDetail:
    @pytest.fixture(scope='class', autouse=True)
    def _class_db(self, django_db_setup, django_db_blocker):
        """a class-scoped version of the `django_db` mark
        (so we can use class-scoped fixtures to set up data
        for use across several tests)
        """
        with django_db_blocker.unblock():
            with transaction.atomic():
                yield

    @pytest.fixture(scope='function', autouse=True)
    def _per_test_transaction(self):
        """wrap each test in a transaction
        (so expected errors don't interfere with the
        class-scoped transaction in _class_db)
        """
        with transaction.atomic():
            yield

    @pytest.fixture(scope='class')
    def user_admin(self):
        return AuthUserFactory()

    @pytest.fixture(scope='class')
    def user_readwrite(self):
        return AuthUserFactory()

    @pytest.fixture(scope='class')
    def user_readonly(self):
        return AuthUserFactory()

    @pytest.fixture(scope='class')
    def user_rando(self):
        return AuthUserFactory()

    @pytest.fixture(scope='class')
    def public_preprint(self, user_admin, user_readwrite, user_readonly):
        preprint = PreprintFactory(creator=user_admin)
        preprint.add_contributor(user_readwrite, permissions=permissions.WRITE)
        preprint.add_contributor(user_readonly, permissions=permissions.READ)
        return preprint

    @pytest.fixture(scope='class')
    def public_preprint_osfguid(self, public_preprint):
        return public_preprint.guids.first()

    @pytest.fixture(scope='class')
    def private_preprint(self, user_admin, user_readwrite, user_readonly):
        preprint = PreprintFactory(is_published=False, creator=user_admin, is_public=False, machine_state='pending')
        preprint.add_contributor(user_readwrite, permissions=permissions.WRITE)
        preprint.add_contributor(user_readonly, permissions=permissions.READ)
        return preprint

    @pytest.fixture(scope='class')
    def private_preprint_osfguid(self, private_preprint):
        return private_preprint.guids.first()

    @pytest.fixture(scope='class')
    def public_project(self, user_admin, user_readwrite, user_readonly):
        project = ProjectFactory(creator=user_admin, is_public=True)
        project.add_contributor(user_readwrite, permissions=permissions.WRITE)
        project.add_contributor(user_readonly, permissions=permissions.READ)
        return project

    @pytest.fixture(scope='class')
    def public_project_osfguid(self, public_project):
        return public_project.guids.first()

    @pytest.fixture(scope='class')
    def private_project(self, user_admin, user_readwrite, user_readonly):
        project = ProjectFactory(creator=user_admin, is_public=False)
        project.add_contributor(user_readwrite, permissions=permissions.WRITE)
        project.add_contributor(user_readonly, permissions=permissions.READ)
        return project

    @pytest.fixture(scope='class')
    def private_project_osfguid(self, private_project):
        return private_project.guids.first()

    @pytest.fixture(scope='class')
    def public_registration(self, public_project):
        return RegistrationFactory(project=public_project, is_public=True)

    @pytest.fixture(scope='class')
    def public_registration_osfguid(self, public_registration):
        return public_registration.guids.first()

    @pytest.fixture(scope='class')
    def private_registration(self, private_project):
        return RegistrationFactory(project=private_project, is_public=False)

    @pytest.fixture(scope='class')
    def private_registration_osfguid(self, private_registration):
        return private_registration.guids.first()

    @pytest.fixture(params=['preprint', 'project', 'registration'])
    def item_type(self, request):
        return request.param

    @pytest.fixture
    def public_osfguid(self, item_type, public_preprint_osfguid, public_project_osfguid, public_registration_osfguid):
        if item_type == 'preprint':
            return public_preprint_osfguid
        if item_type == 'project':
            return public_project_osfguid
        if item_type == 'registration':
            return public_registration_osfguid
        raise NotImplementedError

    @pytest.fixture
    def private_osfguid(self, item_type, private_preprint_osfguid, private_project_osfguid, private_registration_osfguid):
        if item_type == 'preprint':
            return private_preprint_osfguid
        if item_type == 'project':
            return private_project_osfguid
        if item_type == 'registration':
            return private_registration_osfguid
        raise NotImplementedError

    @pytest.fixture(params=['admin', 'readwrite', 'readonly', 'rando'])
    def anybody(self, request, user_admin, user_readwrite, user_readonly, user_rando):
        if request.param == 'admin':
            return user_admin.auth
        if request.param == 'readwrite':
            return user_readwrite.auth
        if request.param == 'readonly':
            return user_readonly.auth
        if request.param == 'rando':
            return user_rando.auth
        raise NotImplementedError

    @pytest.fixture(params=['admin', 'readwrite', 'readonly'])
    def anybody_with_read_permission(self, request, user_admin, user_readwrite, user_readonly):
        if request.param == 'admin':
            return user_admin.auth
        if request.param == 'readwrite':
            return user_readwrite.auth
        if request.param == 'readonly':
            return user_readonly.auth
        raise NotImplementedError

    @pytest.fixture(params=['admin', 'readwrite'])
    def anybody_with_write_permission(self, request, user_admin, user_readwrite):
        if request.param == 'admin':
            return user_admin.auth
        if request.param == 'readwrite':
            return user_readwrite.auth
        raise NotImplementedError

    @pytest.fixture(params=['readonly', 'rando'])
    def anybody_without_write_permission(self, request, user_readonly, user_rando):
        if request.param == 'readonly':
            return user_readonly.auth
        if request.param == 'rando':
            return user_rando.auth
        raise NotImplementedError

    def test_anonymous(self, app, public_osfguid, private_osfguid):
        # can GET public
        res = app.get(make_url(public_osfguid))
        assert res.status_code == 200
        assert res.json['data']['id'] == public_osfguid._id

        # cannot GET private
        res = app.get(
            make_url(private_osfguid),
            expect_errors=True,
        )
        assert res.status_code == 401

        for osfguid in (public_osfguid, private_osfguid):
            # cannot PATCH
            res = app.patch_json_api(
                make_url(osfguid),
                make_payload(osfguid, language='hah'),
                expect_errors=True,
            )
            assert res.status_code == 401

            # cannot PUT
            res = app.put_json_api(
                make_url(osfguid),
                make_payload(osfguid, language='foo'),
                expect_errors=True,
            )
            assert res.status_code == 401

            # everybody cannot DELETE
            res = app.delete_json_api(
                make_url(osfguid),
                expect_errors=True,
            )
            assert res.status_code == 401

    def test_what_everybody_can_do(self, app, public_osfguid, private_osfguid, anybody):
        # can GET public
        res = app.get(
            make_url(public_osfguid),
            auth=anybody,
        )
        assert res.status_code == 200
        assert res.json['data']['id'] == public_osfguid._id

        for osfguid in (public_osfguid, private_osfguid):
            # cannot GET a list view
            res = app.get(
                make_url(None),
                make_payload(osfguid, language='foo'),
                auth=anybody,
                expect_errors=True,
            )
            assert res.status_code == 404

            # cannot POST to a list view
            res = app.post_json_api(
                make_url(None),
                make_payload(osfguid, language='foo'),
                auth=anybody,
                expect_errors=True,
            )
            assert res.status_code == 404

            # cannot POST to a detail view
            res = app.post_json_api(
                make_url(osfguid),
                make_payload(osfguid, language='foo'),
                auth=anybody,
                expect_errors=True,
            )
            assert res.status_code == 405

            # cannot DELETE
            res = app.delete_json_api(
                make_url(osfguid),
                auth=anybody,
                expect_errors=True,
            )
            assert res.status_code == 405

    def test_without_read_permission(self, app, private_osfguid, user_rando):
        # cannot GET private
        res = app.get(
            make_url(private_osfguid),
            auth=user_rando.auth,
            expect_errors=True,
        )
        assert res.status_code == 403

    def test_without_write_permission(self, app, public_osfguid, private_osfguid, anybody_without_write_permission):
        for osfguid in (public_osfguid, private_osfguid):
            # cannot PATCH
            res = app.patch_json_api(
                make_url(osfguid),
                make_payload(osfguid, language='hah'),
                auth=anybody_without_write_permission,
                expect_errors=True,
            )
            assert res.status_code == 403
            # cannot PUT
            res = app.put_json_api(
                make_url(osfguid),
                make_payload(osfguid, language='foo'),
                auth=anybody_without_write_permission,
                expect_errors=True,
            )
            assert res.status_code == 403

    def test_with_read_permission(self, app, private_osfguid, anybody_with_read_permission):
        # can GET private
        res = app.get(
            make_url(private_osfguid),
            auth=anybody_with_read_permission,
        )
        assert res.status_code == 200
        assert res.json['data']['id'] == private_osfguid._id

    def test_with_write_permission(self, app, public_osfguid, private_osfguid, anybody_with_write_permission):
        for osfguid in (public_osfguid, private_osfguid):
            # can PUT
            res = app.put_json_api(
                make_url(osfguid),
                make_payload(osfguid, language='foo'),
                auth=anybody_with_write_permission,
            )
            assert res.status_code == 200

            # can PATCH
            res = app.patch_json_api(
                make_url(osfguid),
                make_payload(osfguid, language='nga-CD'),
                auth=anybody_with_write_permission,
            )
            assert res.status_code == 200
            assert res.json['data']['attributes']['language'] == 'nga-CD'
            dbrecord = GuidMetadataRecord.objects.for_guid(osfguid)
            assert dbrecord.language == 'nga-CD'
        # TODO: assert node.logs.first().action == NodeLog.FILE_METADATA_UPDATED

    # def test_custom_properties(self, app, user_readwrite, public_node_guid):
    #     payload = make_payload(
    #         public_node_guid,
    #         language='en-NZ',
    #         resource_type_general='Text',
    #         custom_properties=[
    #             {
    #                 'property_uri': 'https://my.example/vocab/wibbleforth',
    #                 'value_as_text': 'wobblefirth',
    #             },
    #         ],
    #     )
    #     res = app.patch_json_api(make_url(public_node_guid), payload, auth=user_readwrite.auth)
    #     assert res.status_code == 200
    #     assert res.json['data']['attributes'] == {
    #         'language': 'en-NZ',
    #         'resource_type_general': 'Text',
    #         'funders': [],
    #         'custom_properties': [
    #             {
    #                 'property_uri': 'https://my.example/vocab/wibbleforth',
    #                 'value_as_text': 'wobblefirth',
    #             },
    #         ],
    #     }
    #     metadata_record = public_node_guid.metadata_record
    #     assert metadata_record.language == 'en-NZ'
    #     assert metadata_record.resource_type_general == 'Text'

    # def test_update_fails_with_extra_key(self, app, user_readwrite, public_file_guid):
    #     payload = make_payload(
    #         public_file_guid,
    #         cat='mackerel',
    #     )
    #     res = app.patch_json_api(make_url(public_file_guid), payload, auth=user_readwrite.auth, expect_errors=True)
    #     assert res.status_code == 400
    #     assert 'Additional properties are not allowed' in res.json['errors'][0]['detail']
    #     assert res.json['errors'][0]['meta'].get('metadata_schema', None)
    #     # assert public_record.metadata == {}

    # def test_update_fails_with_invalid_json(self, app, user, public_record, make_payload):
    #     payload = make_payload(public_record)
    #     payload['data']['attributes']['metadata']['related_publication_doi'] = 'dinosaur'
    #     res = app.patch_json_api(make_url(public_record), payload, auth=user.auth, expect_errors=True)
    #     public_record.reload()
    #     assert res.status_code == 400
    #     assert res.json['errors'][0]['detail'] == 'Your response of dinosaur for the field related_publication_doi was invalid.'
    #     assert public_record.metadata == {}

    # def test_cannot_update_registration_metadata_record(self, app, user, registration_record, make_payload):
    #     url = '/{}files/{}/metadata_records/{}/'.format(API_BASE, registration_record.file._id, registration_record._id)
    #     res = app.patch_json_api(url, make_payload(registration_record), auth=user.auth, expect_errors=True)
    #     assert res.status_code == 403

    # def test_update_file_metadata_for_preprint_file(self, app, user_readwrite, preprint_record, preprint):
    #     res = app.patch_json_api(make_url(preprint_record), make_payload(preprint_record), auth=user.auth)
    #     preprint_record.reload()
    #     assert res.status_code == 200
    #     assert res.json['data']['attributes']['metadata'] == metadata_record_json
    #     assert preprint_record.metadata == metadata_record_json
    #     assert preprint.logs.first().action == PreprintLog.FILE_METADATA_UPDATED
