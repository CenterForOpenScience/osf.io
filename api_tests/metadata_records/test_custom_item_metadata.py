import pytest

from api.base.settings.defaults import API_BASE
from osf.models import GuidMetadataRecord, Preprint
from osf.utils import permissions
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    PreprintFactory,
)
from .utils import ExpectedMetadataRecord


@pytest.mark.usefixtures('with_class_scoped_db')
@pytest.mark.django_db
class TestCustomItemMetadataRecordDetail:
    APIV2_PATH = 'custom_item_metadata_records/'
    APIV2_RESOURCE_TYPE = 'custom-item-metadata-record'
    EXPECTED_LOG_ACTION = 'guid_metadata_updated'

    def make_url(self, guid):
        if guid is None:
            return f'/{API_BASE}{self.APIV2_PATH}'
        if hasattr(guid, 'guid'):
            guid = guid.guid
        return f'/{API_BASE}{self.APIV2_PATH}{guid._id}/'

    def make_payload(self, guid, **attributes):
        if hasattr(guid, 'guid'):
            guid = guid.guid
        return {
            'data': {
                'id': guid._id,
                'type': self.APIV2_RESOURCE_TYPE,
                'attributes': attributes,
            }
        }

    def get_loggable_referent(self, osfguid):
        return osfguid.referent

    def assert_expected_log(self, osfguid, user, updated_fields):
        loggable_referent = self.get_loggable_referent(osfguid)
        referent_param = (
            'preprint'
            if isinstance(loggable_referent, Preprint)
            else 'node'
        )
        log = loggable_referent.logs.first()
        assert log.action == self.EXPECTED_LOG_ACTION
        assert log.user == user
        assert log.params[referent_param] == loggable_referent._id
        assert log.params['guid'] == osfguid._id
        assert log.params['urls']['view'] == f'/{osfguid._id}'
        assert log.params['updated_fields'] == updated_fields
        return log

    @pytest.fixture(scope='class')
    def user_admin(self):
        return AuthUserFactory(username='some admin')

    @pytest.fixture(scope='class')
    def user_readwrite(self):
        return AuthUserFactory(username='some readwrite')

    @pytest.fixture(scope='class')
    def user_readonly(self):
        return AuthUserFactory(username='some readonly')

    @pytest.fixture(scope='class')
    def user_rando(self):
        return AuthUserFactory(username='some rando')

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
            return user_admin
        if request.param == 'readwrite':
            return user_readwrite
        if request.param == 'readonly':
            return user_readonly
        if request.param == 'rando':
            return user_rando
        raise NotImplementedError

    @pytest.fixture(params=['admin', 'readwrite', 'readonly'])
    def anybody_with_read_permission(self, request, user_admin, user_readwrite, user_readonly):
        if request.param == 'admin':
            return user_admin
        if request.param == 'readwrite':
            return user_readwrite
        if request.param == 'readonly':
            return user_readonly
        raise NotImplementedError

    @pytest.fixture(params=['admin', 'readwrite'])
    def anybody_with_write_permission(self, request, user_admin, user_readwrite):
        if request.param == 'admin':
            return user_admin
        if request.param == 'readwrite':
            return user_readwrite
        raise NotImplementedError

    @pytest.fixture(params=['readonly', 'rando'])
    def anybody_without_write_permission(self, request, user_readonly, user_rando):
        if request.param == 'readonly':
            return user_readonly
        if request.param == 'rando':
            return user_rando
        raise NotImplementedError

    def test_anonymous(self, app, public_osfguid, private_osfguid):
        # can GET public
        res = app.get(self.make_url(public_osfguid))
        assert res.status_code == 200
        assert res.json['data']['id'] == public_osfguid._id

        # cannot GET private
        res = app.get(
            self.make_url(private_osfguid),
            expect_errors=True,
        )
        assert res.status_code == 401

        for osfguid in (public_osfguid, private_osfguid):
            # cannot PATCH
            res = app.patch_json_api(
                self.make_url(osfguid),
                self.make_payload(osfguid, language='hah'),
                expect_errors=True,
            )
            assert res.status_code == 401

            # cannot PUT
            res = app.put_json_api(
                self.make_url(osfguid),
                self.make_payload(osfguid, language='foo'),
                expect_errors=True,
            )
            assert res.status_code == 401

            # everybody cannot DELETE
            res = app.delete_json_api(
                self.make_url(osfguid),
                expect_errors=True,
            )
            assert res.status_code == 401

    def test_what_everybody_can_do(self, app, public_osfguid, private_osfguid, anybody):
        # can GET public
        res = app.get(
            self.make_url(public_osfguid),
            auth=anybody.auth,
        )
        assert res.status_code == 200
        assert res.json['data']['id'] == public_osfguid._id

        for osfguid in (public_osfguid, private_osfguid):
            # cannot GET a list view
            res = app.get(
                self.make_url(None),
                self.make_payload(osfguid, language='foo'),
                auth=anybody.auth,
                expect_errors=True,
            )
            assert res.status_code == 404

            # cannot POST to a list view
            res = app.post_json_api(
                self.make_url(None),
                self.make_payload(osfguid, language='foo'),
                auth=anybody.auth,
                expect_errors=True,
            )
            assert res.status_code == 404

            # cannot POST to a detail view
            res = app.post_json_api(
                self.make_url(osfguid),
                self.make_payload(osfguid, language='foo'),
                auth=anybody.auth,
                expect_errors=True,
            )
            assert res.status_code == 405

            # cannot DELETE
            res = app.delete_json_api(
                self.make_url(osfguid),
                auth=anybody.auth,
                expect_errors=True,
            )
            assert res.status_code == 405

    def test_without_read_permission(self, app, private_osfguid, user_rando):
        # cannot GET private
        res = app.get(
            self.make_url(private_osfguid),
            auth=user_rando.auth,
            expect_errors=True,
        )
        assert res.status_code == 403

    def test_without_write_permission(self, app, public_osfguid, private_osfguid, anybody_without_write_permission):
        for osfguid in (public_osfguid, private_osfguid):
            # cannot PATCH
            res = app.patch_json_api(
                self.make_url(osfguid),
                self.make_payload(osfguid, language='hah'),
                auth=anybody_without_write_permission.auth,
                expect_errors=True,
            )
            assert res.status_code == 403
            # cannot PUT
            res = app.put_json_api(
                self.make_url(osfguid),
                self.make_payload(osfguid, language='foo'),
                auth=anybody_without_write_permission.auth,
                expect_errors=True,
            )
            assert res.status_code == 403

    def test_with_read_permission(self, app, private_osfguid, anybody_with_read_permission):
        # can GET private
        res = app.get(
            self.make_url(private_osfguid),
            auth=anybody_with_read_permission.auth,
        )
        assert res.status_code == 200
        assert res.json['data']['id'] == private_osfguid._id

    def test_with_write_permission(self, app, public_osfguid, private_osfguid, anybody_with_write_permission):
        for osfguid in (public_osfguid, private_osfguid):
            expected = ExpectedMetadataRecord()
            expected.id = osfguid._id

            # can PUT
            expected.language = 'nga'
            expected.resource_type_general = 'Text'
            res = app.put_json_api(
                self.make_url(osfguid),
                self.make_payload(
                    osfguid,
                    language='nga',
                    resource_type_general='Text',
                ),
                auth=anybody_with_write_permission.auth,
            )
            assert res.status_code == 200
            db_record = GuidMetadataRecord.objects.get(guid=osfguid)
            expected.assert_expectations(db_record=db_record, api_record=res.json['data'])
            self.assert_expected_log(
                osfguid,
                user=anybody_with_write_permission,
                updated_fields={
                    'language': {'old': '', 'new': 'nga'},
                    'resource_type_general': {'old': '', 'new': 'Text'},
                },
            )

            # can PATCH
            expected.language = 'nga-CD'
            res = app.patch_json_api(
                self.make_url(osfguid),
                self.make_payload(osfguid, language='nga-CD'),
                auth=anybody_with_write_permission.auth,
            )
            assert res.status_code == 200
            expected.assert_expectations(db_record=db_record, api_record=res.json['data'])
            self.assert_expected_log(
                osfguid,
                user=anybody_with_write_permission,
                updated_fields={
                    'language': {'old': 'nga', 'new': 'nga-CD'},
                },
            )

            # can PATCH funders
            good_funding_infos = (
                [{
                    'funder_name': 'hell-o',
                    'funder_identifier': 'https://hello.example/money',
                    'funder_identifier_type': 'Other',
                    'award_number': '7',
                    'award_uri': 'http://award.example/7',
                    'award_title': 'award seven',
                }],
                [{
                    'funder_name': 'hell-o',
                    'funder_identifier': 'https://hello.example/money',
                    'funder_identifier_type': 'Crossref Funder ID',
                    'award_number': '7',
                    'award_uri': 'http://award.example/7',
                    'award_title': 'award seven',
                }, {
                    'funder_name': 'shell-o',
                    'funder_identifier': 'https://shello.example/smelly-money',
                    'funder_identifier_type': 'ROR',
                    'award_number': 'splevin',
                    'award_uri': 'http://shello.example/award-number-splevin',
                    'award_title': 'award splevin',
                }],
                [{
                    'funder_name': 'funder_name',
                }, {
                    'funder_name': 'is',
                }, {
                    'funder_name': 'enough',
                }],
                [{
                    'funder_name': 'NIH probably',
                    'funder_identifier': 'https://doi.org/10.blah/deeblah',
                    'funder_identifier_type': 'Crossref Funder ID',
                    'award_number': '27',
                    'award_uri': 'https://awards.example/twenty-seven',
                    'award_title': 'Award Twentyseven',
                }, {
                    'funder_name': 'NSF probably',
                    'funder_identifier': 'https://doi.org/10.blah/dooblah',
                    'funder_identifier_type': 'Crossref Funder ID',
                    'award_number': '28',
                    'award_uri': 'https://awards.example/twenty-eight',
                    'award_title': 'Award Twentyeight',
                }, {
                    'funder_name': 'Mx. Moneypockets',
                    'funder_identifier': '',
                    'funder_identifier_type': '',
                    'award_number': '10000000',
                    'award_uri': 'https://moneypockets.example/millions',
                    'award_title': 'Because i said so',
                }],
                [],
            )
            previous_funding_info = []
            for good_funding_info in good_funding_infos:
                expected.funding_info = good_funding_info
                res = app.patch_json_api(
                    self.make_url(osfguid),
                    self.make_payload(osfguid, funders=good_funding_info),
                    auth=anybody_with_write_permission.auth,
                )
                assert res.status_code == 200
                expected.assert_expectations(db_record=db_record, api_record=res.json['data'])
                self.assert_expected_log(
                    osfguid,
                    user=anybody_with_write_permission,
                    updated_fields={
                        'funding_info': {'old': previous_funding_info, 'new': expected.funding_info},
                    },
                )
                previous_funding_info = expected.funding_info

            # funders cleaned
            cleaned_funding_infos = (
                (
                    [{'funder_name': 'hello', 'extra': 'ignored'}],  # given
                    [{'funder_name': 'hello'}],  # cleaned
                ),
                (
                    [{'funder_name': 'foo', 'award_number': 7}],  # given
                    [{'funder_name': 'foo', 'award_number': '7'}],  # cleaned
                ),
            )
            for given_funding_info, cleaned_funding_info in cleaned_funding_infos:
                expected.funding_info = cleaned_funding_info
                res = app.patch_json_api(
                    self.make_url(osfguid),
                    self.make_payload(osfguid, funders=given_funding_info),
                    auth=anybody_with_write_permission.auth,
                )
                assert res.status_code == 200
                expected.assert_expectations(db_record=db_record, api_record=res.json['data'])
                self.assert_expected_log(
                    osfguid,
                    user=anybody_with_write_permission,
                    updated_fields={
                        'funding_info': {'old': previous_funding_info, 'new': expected.funding_info},
                    },
                )
                previous_funding_info = expected.funding_info

            # funders validated
            bad_funding_infos = (
                {
                    'bad': [{}],
                    'expected_errors': [{'source': {'pointer': '/data/attributes/funders/funder_name'}, 'detail': ['This field is required.']}],
                }, {
                    'bad': [{'funder_name': 'good'}, {}, {}],
                    'expected_errors': [
                        {'source': {'pointer': '/data/attributes/funders/funder_name'}, 'detail': ['This field is required.']},
                        {'source': {'pointer': '/data/attributes/funders/funder_name'}, 'detail': ['This field is required.']},
                    ],
                }, {
                    'bad': [{'award_number': '7'}],
                    'expected_errors': [{'source': {'pointer': '/data/attributes/funders/funder_name'}, 'detail': ['This field is required.']}],
                }, {
                    'bad': [{'funder_name': 'foo', 'award_number': {'number': '7'}}],
                    'expected_errors': [{'source': {'pointer': '/data/attributes/funders/award_number'}, 'detail': ['Not a valid string.']}],
                }, {
                    'bad': [{'funder_name': 'foo', 'award_uri': 'not a uri'}],
                    'expected_errors': [{'source': {'pointer': '/data/attributes/funders/award_uri'}, 'detail': ['Enter a valid URL.']}],
                }, {
                    'bad': [{'funder_name': 'foo', 'funder_identifier_type': 'not one of the choices'}],
                    'expected_errors': [{'source': {'pointer': '/data/attributes/funders/funder_identifier_type'}, 'detail': ['"not one of the choices" is not a valid choice.']}],
                },
            )
            for bad_funding_info in bad_funding_infos:
                res = app.patch_json_api(
                    self.make_url(osfguid),
                    self.make_payload(osfguid, funders=bad_funding_info['bad']),
                    auth=anybody_with_write_permission.auth,
                    expect_errors=True,
                )
                assert res.status_code == 400
                assert res.json['errors'] == bad_funding_info['expected_errors']
                # check it hasn't changed in the db
                expected.assert_expectations(db_record=db_record, api_record=None)
