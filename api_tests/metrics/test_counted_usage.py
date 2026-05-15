from datetime import datetime, timezone
from unittest import mock

import pytest
from elasticsearch_metrics.util.anon_enough import opaque_key

from framework.auth.core import Auth
from osf.metadata.rdfutils import OSF
from osf.utils.permissions import ADMIN, READ, WRITE

from api_tests.utils import create_test_file
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    PreprintFactory,
    PrivateLinkFactory,
    ProjectFactory,
    RegistrationFactory,
)


COUNTED_USAGE_URL = '/_/metrics/events/counted_usage/'

def counted_usage_payload(**attributes):
    return {
        'data': {
            'type': 'counted-usage',
            'attributes': attributes,
        },
    }


def assert_saved_with(mock_es8, *, expected_doc_id=None, expected_attrs):
    assert mock_es8.index.call_count == 1
    _args, _kwargs = mock_es8.index.call_args
    if expected_doc_id is not None:
        assert _kwargs['id'] == expected_doc_id
    _actual_attrs = _kwargs['body']
    for _attr_name, _expected_value in expected_attrs.items():
        _actual_value = _actual_attrs.get(_attr_name, None)
        assert (_actual_value == _expected_value), repr(_actual_value)


@pytest.fixture
def mock_es8():
    with mock.patch('elasticsearch_metrics.imps.elastic8.TimeseriesRecord.check_djelme_setup'):
        with mock.patch('elasticsearch_metrics.imps.elastic8.BaseDjelmeRecord._get_connection') as _mock_get_connection:
            _mock_es8 = _mock_get_connection.return_value
            _mock_es8.index.return_value = {'result': {}}
            yield _mock_es8


@pytest.mark.django_db
class TestRestrictions:
    def test_http_method(self, app):
        resp = app.put(COUNTED_USAGE_URL, expect_errors=True)
        assert resp.status_code == 405
        resp = app.get(COUNTED_USAGE_URL, expect_errors=True)
        assert resp.status_code == 405
        resp = app.patch(COUNTED_USAGE_URL, expect_errors=True)
        assert resp.status_code == 405
        resp = app.delete(COUNTED_USAGE_URL, expect_errors=True)
        assert resp.status_code == 405

    @pytest.mark.parametrize('attrs', [
        {},
        {'item_guid': 'foo', 'action_labels': []},
        {'action_labels': []},
        {'pageview_info': {'page_url': 'http://example.foo/blahblah/blee'}},
    ])
    def test_required_attributes(self, app, attrs):
        payload = counted_usage_payload(**attrs)
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, expect_errors=True)
        assert resp.status_code == 400


@pytest.mark.django_db
class TestComputedFields:

    @pytest.fixture(autouse=True)
    def mock_domain(self):
        domain = 'http://example.foo/'
        with mock.patch('website.settings.DOMAIN', new=domain):
            yield domain

    @pytest.fixture(autouse=True)
    def mock_now(self):
        timestamp = datetime(1981, 1, 1, 0, 1, 31, tzinfo=timezone.utc)
        with (
            mock.patch('django.utils.timezone.now', return_value=timestamp),
            mock.patch('elasticsearch_metrics.imps.elastic8.utcnow', return_value=timestamp),
        ):
            yield timestamp

    @pytest.fixture
    def preprint(self, request):
        return PreprintFactory(
            is_public=True,
            is_published=True,
        )

    @pytest.fixture()
    def user(self):
        with mock.patch('osf.models.base.generate_guid', return_value='guidy'):
            return AuthUserFactory()

    def test_by_client_session_id(self, app, mock_es8, user, preprint):
        payload = counted_usage_payload(
            client_session_id='hello',
            item_guid=preprint._id,
            action_labels=['view', 'api'],
            pageview_info={'page_url': 'http://example.foo/blahblah/blee'},
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers)
        assert resp.status_code == 201
        _expected_sessionhour_id = opaque_key(['hello', '1981-01-01', '0'])
        assert_saved_with(
            mock_es8,
            expected_doc_id=opaque_key([
                'http://example.foo/',
                _expected_sessionhour_id,
                "['api', 'view']",
                'http://example.foo/blahblah/blee',
                '1981-01-01',
                '3',
            ]),
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'item_osfid': preprint._id,
                'item_type': str(OSF.Preprint),
                'sessionhour_id': _expected_sessionhour_id,
                'action_labels': ['api', 'view'],
                'pageview_info': {
                    'page_url': 'http://example.foo/blahblah/blee',
                    'page_path': '/blahblah/blee',
                    'hour_of_day': 0,
                },
            },
        )

    def test_by_client_session_id_anon(self, app, mock_es8, preprint):
        payload = counted_usage_payload(
            client_session_id='hihi',
            item_guid=preprint._id,
            action_labels=['view', 'web'],
            pageview_info={
                'page_url': 'http://example.foo/bliz/',
                'referer_url': 'http://elsewhere.baz/index.php',
            },
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers)
        assert resp.status_code == 201
        _expected_sessionhour_id = opaque_key(['hihi', '1981-01-01', '0'])
        assert_saved_with(
            mock_es8,
            expected_doc_id=opaque_key([
                'http://example.foo/',
                _expected_sessionhour_id,
                "['view', 'web']",
                'http://example.foo/bliz/',
                '1981-01-01',
                '3',
            ]),
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'item_osfid': preprint._id,
                'item_type': str(OSF.Preprint),
                'sessionhour_id': _expected_sessionhour_id,
                'action_labels': ['view', 'web'],
                'pageview_info': {
                    'page_url': 'http://example.foo/bliz/',
                    'page_path': '/bliz',
                    'referer_url': 'http://elsewhere.baz/index.php',
                    'referer_domain': 'elsewhere.baz',
                    'hour_of_day': 0,
                },
            },
        )

    def test_by_user_auth(self, app, mock_es8, user, preprint):
        payload = counted_usage_payload(
            item_guid=preprint._id,
            action_labels=['view', 'web'],
            pageview_info={
                'page_url': 'http://osf.io/mst3k',
                'referer_url': 'http://osf.io/registries/discover',
            },
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers, auth=user.auth)
        assert resp.status_code == 201
        _expected_sessionhour_id = opaque_key(['guidy', '1981-01-01', '0'])
        assert_saved_with(
            mock_es8,
            expected_doc_id=opaque_key([
                'http://example.foo/',
                _expected_sessionhour_id,
                "['view', 'web']",
                'http://osf.io/mst3k',
                '1981-01-01',
                '3',
            ]),
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'item_osfid': preprint._id,
                'item_type': str(OSF.Preprint),
                'sessionhour_id': _expected_sessionhour_id,
                'action_labels': ['view', 'web'],
                'pageview_info': {
                    'page_url': 'http://osf.io/mst3k',
                    'page_path': '/mst3k',
                    'referer_url': 'http://osf.io/registries/discover',
                    'referer_domain': 'osf.io',
                    'hour_of_day': 0,
                },
            },
        )

    def test_by_useragent_header(self, app, mock_es8, preprint):
        payload = counted_usage_payload(
            item_guid=preprint._id,
            action_labels=['view', 'api'],
            pageview_info={
                'page_url': 'http://example.foo/bliz/',
                'referer_url': 'http://elsewhere.baz/index.php',
            },
        )
        headers = {
            'User-Agent': 'haha',
        }
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers=headers)
        assert resp.status_code == 201
        _expected_sessionhour_id = opaque_key(['localhost:80', 'haha', '1981-01-01', '0'])
        assert_saved_with(
            mock_es8,
            expected_doc_id=opaque_key([
                'http://example.foo/',
                _expected_sessionhour_id,
                "['api', 'view']",
                'http://example.foo/bliz/',
                '1981-01-01',
                '3',
            ]),
            expected_attrs={
                'platform_iri': 'http://example.foo/',
                'item_osfid': preprint._id,
                'item_type': str(OSF.Preprint),
                'sessionhour_id': opaque_key(['localhost:80', 'haha', '1981-01-01', '0']),
                'action_labels': ['api', 'view'],
                'pageview_info': {
                    'page_url': 'http://example.foo/bliz/',
                    'page_path': '/bliz',
                    'referer_url': 'http://elsewhere.baz/index.php',
                    'referer_domain': 'elsewhere.baz',
                    'hour_of_day': 0,
                },
            },
        )


@pytest.mark.parametrize('item_public', [True, False])
@pytest.mark.django_db
class TestGuidFields:

    @pytest.fixture(autouse=True)
    def mock_domain(self):
        domain = 'http://example.foo/'
        with mock.patch('website.settings.DOMAIN', new=domain):
            yield domain

    @pytest.fixture
    def preprint(self, item_public):
        return PreprintFactory(
            is_public=item_public,
            is_published=item_public,
        )

    @pytest.fixture
    def preprint_guid(self, preprint):
        return preprint._id

    @pytest.fixture
    def preprint_file_guid(self, preprint):
        return preprint.primary_file.get_guid(create=True)._id

    @pytest.fixture
    def parent_reg(self, item_public):
        return RegistrationFactory(is_public=item_public)

    @pytest.fixture
    def child_reg(self, parent_reg, item_public):
        return RegistrationFactory(
            is_public=item_public,
            project=NodeFactory(parent=parent_reg.registered_from),
            parent=parent_reg,
        )

    @pytest.fixture
    def child_reg_file(self, child_reg):
        return create_test_file(
            target=child_reg,
            user=AuthUserFactory(),
        )

    @pytest.fixture
    def child_reg_file_guid(self, child_reg_file):
        return child_reg_file.get_guid(create=True)._id

    def test_preprint_file(self, app, mock_es8, preprint, item_public, mock_domain):
        # test_preprint_guid
        payload = counted_usage_payload(
            item_guid=preprint._id,
            action_labels=['view', 'web'],
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers={'User-Agent': 'blarg'})
        assert resp.status_code == 201
        assert_saved_with(
            mock_es8,
            expected_attrs={
                'item_osfid': preprint._id,
                'item_iri': f'{mock_domain}{preprint._id}',
                'item_type': str(OSF.Preprint),
                'item_public': item_public,
                'provider_id': preprint.provider._id,
                'database_iri': f'{mock_domain}preprints/{preprint.provider._id}',
                'within_iris': [f'{mock_domain}{preprint._id}'],
            },
        )
        mock_es8.reset_mock()

        # test_preprint_file_guid
        payload = counted_usage_payload(
            item_guid=preprint.primary_file.get_guid(create=True)._id,
            action_labels=['view', 'web'],
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers={'User-Agent': 'blarg'})
        assert resp.status_code == 201
        assert_saved_with(
            mock_es8,
            expected_attrs={
                'item_osfid': preprint.primary_file.get_guid()._id,
                'item_iri': preprint.primary_file.get_semantic_iri(),
                'item_type': str(OSF.File),
                'item_public': item_public,
                'provider_id': preprint.primary_file.provider,
                'database_iri': f'urn:files.osf.io:{preprint.primary_file.provider}',
                'within_iris': sorted([
                    f'{mock_domain}{preprint._id}',
                    preprint.primary_file.get_semantic_iri(),
                ]),
            },
        )

    def test_child_registration_file(self, app, mock_es8, child_reg_file_guid, child_reg_file, child_reg, parent_reg, item_public, mock_domain):
        # test_child_registration_file_guid
        payload = counted_usage_payload(
            item_guid=child_reg_file_guid,
            action_labels=['view', 'web'],
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers={'User-Agent': 'blarg'})
        assert resp.status_code == 201
        assert_saved_with(
            mock_es8,
            expected_attrs={
                'action_labels': ['view', 'web'],
                'item_osfid': child_reg_file_guid,
                'item_type': str(OSF.File),
                'item_public': item_public,
                'provider_id': 'osfstorage',
                'database_iri': 'urn:files.osf.io:osfstorage',
                'within_iris': sorted([
                    child_reg_file.get_semantic_iri(),
                    child_reg.get_semantic_iri(),
                    parent_reg.get_semantic_iri(),
                ]),
            },
        )
        mock_es8.reset_mock()

        # test_child_registration_guid
        payload = counted_usage_payload(
            item_guid=child_reg._id,
            action_labels=['view', 'web'],
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers={'User-Agent': 'blarg'})
        assert resp.status_code == 201
        assert_saved_with(
            mock_es8,
            expected_attrs={
                'action_labels': ['view', 'web'],
                'item_osfid': child_reg._id,
                'item_type': str(OSF.RegistrationComponent),
                'item_public': item_public,
                'provider_id': 'osf',
                'database_iri': f'{mock_domain}registries/osf',
                'item_iri': child_reg.get_semantic_iri(),
                'within_iris': sorted([
                    child_reg.get_semantic_iri(),
                    parent_reg.get_semantic_iri(),
                ]),
            },
        )
        mock_es8.reset_mock()

        # test_parent_registration_guid
        payload = counted_usage_payload(
            item_guid=parent_reg._id,
            action_labels=['view', 'web'],
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, headers={'User-Agent': 'blarg'})
        assert resp.status_code == 201
        assert_saved_with(
            mock_es8,
            expected_attrs={
                'action_labels': ['view', 'web'],
                'item_osfid': parent_reg._id,
                'item_public': item_public,
                'provider_id': 'osf',
                'database_iri': f'{mock_domain}registries/osf',
                'item_iri': parent_reg.get_semantic_iri(),
                'within_iris': [parent_reg.get_semantic_iri()],
            },
        )


@pytest.mark.django_db
class TestContributorExclusion:

    def test_creator_pageview_not_recorded(self, app, mock_es8):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        payload = counted_usage_payload(
            item_guid=project._id,
            action_labels=['view', 'web'],
            pageview_info={'page_url': f'https://osf.io/{project._id}/'},
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, auth=user.auth)
        assert resp.status_code == 204
        assert mock_es8.index.call_count == 0

    @pytest.mark.parametrize(
        'permissions',
        [READ, WRITE, ADMIN],
        ids=['read', 'write', 'admin'],
    )
    def test_contributor_pageview_not_recorded(self, app, mock_es8, permissions):
        creator = AuthUserFactory()
        contributor = AuthUserFactory()
        project = ProjectFactory(creator=creator)
        project.add_contributor(contributor, permissions=permissions, auth=Auth(creator))
        payload = counted_usage_payload(
            item_guid=project._id,
            action_labels=['view', 'web'],
            pageview_info={'page_url': f'https://osf.io/{project._id}/analytics/'},
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, auth=contributor.auth)
        assert resp.status_code == 204
        assert mock_es8.index.call_count == 0

    def test_non_contributor_pageview_recorded(self, app, mock_es8):
        creator = AuthUserFactory()
        visitor = AuthUserFactory()
        project = ProjectFactory(creator=creator, is_public=True)
        payload = counted_usage_payload(
            item_guid=project._id,
            action_labels=['view', 'web'],
            pageview_info={'page_url': f'https://osf.io/{project._id}/'},
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, auth=visitor.auth)
        assert resp.status_code == 201
        assert mock_es8.index.call_count == 1

    def test_parent_contributor_not_on_child_component_pageview_recorded(self, app, mock_es8):
        creator = AuthUserFactory()
        child_owner = AuthUserFactory()
        parent_reader = AuthUserFactory()
        parent = ProjectFactory(creator=creator, is_public=True)
        child = NodeFactory(parent=parent, creator=child_owner, is_public=True)
        parent.add_contributor(parent_reader, permissions=ADMIN, auth=Auth(creator))
        assert not child.contributors_and_group_members.filter(guids___id=parent_reader._id).exists()
        payload = counted_usage_payload(
            item_guid=child._id,
            action_labels=['view', 'web'],
            pageview_info={'page_url': f'https://osf.io/{child._id}/'},
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, auth=parent_reader.auth)
        assert resp.status_code == 201
        assert mock_es8.index.call_count == 1

    def test_anonymous_view_only_link_visitor_pageview_recorded(self, app, mock_es8):
        creator = AuthUserFactory()
        project = ProjectFactory(creator=creator, is_public=False)
        link = PrivateLinkFactory(anonymous=True, creator=creator)
        link.nodes.add(project)
        payload = counted_usage_payload(
            item_guid=project._id,
            action_labels=['view', 'web'],
            client_session_id='vol-client-session',
            pageview_info={
                'page_url': f'https://osf.io/{project._id}/?view_only={link.key}',
            },
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload)
        assert resp.status_code == 201
        assert mock_es8.index.call_count == 1

    def test_logged_in_non_contributor_view_only_link_pageview_recorded(self, app, mock_es8):
        creator = AuthUserFactory()
        visitor = AuthUserFactory()
        project = ProjectFactory(creator=creator, is_public=False)
        link = PrivateLinkFactory(anonymous=False, creator=creator)
        link.nodes.add(project)
        payload = counted_usage_payload(
            item_guid=project._id,
            action_labels=['view', 'web'],
            pageview_info={
                'page_url': f'https://osf.io/{project._id}/files/?view_only={link.key}',
            },
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, auth=visitor.auth)
        assert resp.status_code == 201
        assert mock_es8.index.call_count == 1

    @pytest.mark.parametrize(
        'permissions',
        [READ, WRITE, ADMIN],
        ids=['read', 'write', 'admin'],
    )
    def test_logged_in_contributor_view_only_link_pageview_not_recorded(self, app, mock_es8, permissions):
        creator = AuthUserFactory()
        contributor = AuthUserFactory()
        project = ProjectFactory(creator=creator, is_public=False)
        project.add_contributor(contributor, permissions=permissions, auth=Auth(creator))
        link = PrivateLinkFactory(anonymous=False, creator=creator)
        link.nodes.add(project)
        payload = counted_usage_payload(
            item_guid=project._id,
            action_labels=['view', 'web'],
            pageview_info={
                'page_url': f'https://osf.io/{project._id}/?view_only={link.key}',
            },
        )
        resp = app.post_json_api(COUNTED_USAGE_URL, payload, auth=contributor.auth)
        assert resp.status_code == 204
        assert mock_es8.index.call_count == 0
