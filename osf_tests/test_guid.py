from unittest import mock
import pytest
from urllib.parse import quote

from django.utils import timezone
from django.core.exceptions import MultipleObjectsReturned
from framework.auth import Auth


from osf.models import Guid, NodeLicenseRecord, OSFUser, GuidVersionsThrough
from osf.models.base import VersionedGuidMixin
from osf_tests.factories import AuthUserFactory, UserFactory, NodeFactory, NodeLicenseRecordFactory, \
    RegistrationFactory, PreprintFactory, PreprintProviderFactory
from osf.utils.permissions import ADMIN
from osf.models import Preprint
from tests.base import OsfTestCase
from tests.test_websitefiles import TestFile
from website.settings import MFR_SERVER_URL, WATERBUTLER_URL


@pytest.mark.django_db
class TestGuid:

    def test_long_id_gets_generated_on_creation(self):
        obj = NodeLicenseRecordFactory()
        assert obj._id
        assert len(obj._id) > 5

    def test_loading_by_object_id(self):
        obj = NodeLicenseRecordFactory()
        assert NodeLicenseRecord.load(obj._id) == obj

    def test_loading_by_short_guid(self):
        obj = UserFactory()
        assert OSFUser.load(obj._id) == obj

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory,
        RegistrationFactory,
    ])
    def test_short_guid_gets_generated_on_creation(self, Factory):
        obj = Factory()
        assert obj._id
        assert len(obj._id) == 5

@pytest.mark.django_db
class TestReferent:

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory
    ])
    def test_referent(self, Factory):
        obj = Factory()
        guid = Guid.objects.get(_id=obj._id)
        assert guid.referent == obj

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory
    ])
    def test_referent_can_be_set(self, Factory):
        obj = Factory()
        obj1 = Factory()

        guid = Guid.load(obj._id)
        assert guid.referent == obj  # sanity check

        guid.referent = obj1
        assert guid.referent == obj1

    @pytest.mark.skip('I don\'t actually think we do this anywhere')
    def test_swapping_guids(self):
        user = UserFactory()
        node = NodeFactory()

        user_guid = user.guids[0]
        node_guid = node.guids[0]

        user._id = node_guid._id
        node._id = user_guid._id

        assert node_guid._id == user._id
        assert user_guid._id == node._id

    def test_id_matches(self):
        user = UserFactory()
        guid = Guid.objects.get(_id=user._id)

        assert user._id == guid._id

    @pytest.mark.skip('I don\'t actually think we do this anywhere')
    @pytest.mark.parametrize('Factory',
     [
         UserFactory,
         NodeFactory
     ])
    def test_nulling_out_guid(self, Factory):
        obj = Factory()

        guid = Guid.load(obj._id)

        obj.guid = None

        obj.save()
        obj.refresh_from_db()

        # queryset cache returns the old version
        guid.refresh_from_db()

        assert obj.guid != guid

        assert guid.guid != obj.guid.guid

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory,
    ])
    def test_querying_with_multiple_guids(self, Factory):

        obj = Factory()
        guids = [obj.guids.first()]

        for i in range(0, 16):
            guids.append(Guid.objects.create(referent=obj))

        try:
            Factory._meta.model.objects.get(id=obj.id)
        except MultipleObjectsReturned as ex:
            pytest.fail(f'Multiple objects returned for {Factory._meta.model} with multiple guids. {ex}')


@pytest.mark.enable_bookmark_creation
class TestResolveGuid(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.node = NodeFactory()

    def test_resolve_guid(self):
        with mock.patch('framework.csrf.handlers.get_current_user_id', return_value=self.node.creator_id):
            res_guid = self.app.get(self.node.web_url_for('node_setting', _guid=True), auth=self.node.creator.auth)
            res_full = self.app.get(self.node.web_url_for('node_setting'), auth=self.node.creator.auth)
        assert res_guid.text == res_full.text

    def test_resolve_guid_no_referent(self):
        guid = Guid.load(self.node._id)
        guid.referent = None
        guid.save()
        res = self.app.get(
            self.node.web_url_for('node_setting', _guid=True),
            auth=self.node.creator.auth,
        )
        assert res.status_code == 404

    @mock.patch('osf.models.node.Node.deep_url', None)
    def test_resolve_guid_no_url(self):
        res = self.app.get(
            self.node.web_url_for('node_setting', _guid=True),
            auth=self.node.creator.auth,
        )
        assert res.status_code == 404

    def test_resolve_guid_no_auth_redirect_to_cas_includes_public(self):
        """
        Unauthenticated users are sent to login when visiting private projects, but not if the projects are public.
        """
        res = self.app.get(
            self.node.web_url_for('resolve_guid', guid=self.node._id),
        )
        assert res.status_code == 302
        assert '/login?service=' in res.location

        self.node.is_public = True
        self.node.save()
        res = self.app.get(
            self.node.web_url_for('resolve_guid', guid=self.node._id),
        )
        assert res.status_code == 200

    def test_resolve_guid_no_auth_redirect_to_cas_includes_public_with_url_segments(self):
        """
        Unauthenticated users are sent to login when visiting private projects related URLs, but not if the projects are
        public
        """
        for segment in ('comments', 'links', 'components', 'files', 'files/osfstorage', 'files/addon'):
            self.node.is_public = False
            self.node.save()
            res = self.app.get(
                f'{self.node.web_url_for("resolve_guid", guid=self.node._id)}/{segment}/',
            )
            assert res.status_code == 302
            assert '/login?service=' in res.location

            self.node.is_public = True
            self.node.save()
            res = self.app.get(
                f'{self.node.web_url_for("resolve_guid", guid=self.node._id)}/{segment}/',
            )
            assert res.status_code == 200

    def test_resolve_guid_private_request_access_or_redirect_to_cas(self):
        """
        Authenticated users are sent to the request access page when it is set to true on the node, otherwise they get a
        legacy Forbidden page.
        """
        non_contrib = AuthUserFactory()
        self.node.access_requests_enabled = False
        self.node.save()
        res = self.app.get(
            self.node.web_url_for('resolve_guid', guid=self.node._id),
            auth=non_contrib.auth,
        )
        assert '<title>OSF | Forbidden</title>' in res.text
        assert res.status_code == 403

        self.node.access_requests_enabled = True
        self.node.save()
        res = self.app.get(
            self.node.web_url_for('resolve_guid', guid=self.node._id),
            auth=non_contrib.auth,
        )
        assert res.status_code == 403
        assert '<title>OSF | Request Access</title>' in res.text

    def test_resolve_guid_download_file(self):
        pp = PreprintFactory(finish=True)

        res = self.app.get(pp.url + 'download')
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=1' in res.location

        res = self.app.get(pp.url + 'download/')
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=1' in res.location

        res = self.app.get(f'/{pp.primary_file.get_guid(create=True)._id}/download')
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=1' in res.location

        pp.primary_file.create_version(
            creator=pp.creator,
            location={'folder': 'osf', 'object': 'deadbe', 'service': 'cloud'},
            metadata={'contentType': 'img/png', 'size': 9001}
        )
        pp.primary_file.save()

        res = self.app.get(pp.url + 'download/')
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=2' in res.location

        res = self.app.get(pp.url + 'download/?version=1')
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?version=1&action=download&direct' in res.location

        unpub_pp = PreprintFactory(project=self.node, is_published=False)
        res = self.app.get(unpub_pp.url + 'download/?version=1', auth=unpub_pp.creator.auth)
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{unpub_pp._id}/providers/{unpub_pp.primary_file.provider}{unpub_pp.primary_file.path}?version=1&action=download&direct' in res.location

    @mock.patch('website.settings.USE_EXTERNAL_EMBER', True)
    @mock.patch('website.settings.EXTERNAL_EMBER_APPS', {
        'preprints': {
            'server': 'http://localhost:4200',
            'path': '/preprints/'
        },
    })
    def test_resolve_guid_download_file_from_emberapp_preprints(self):
        provider = PreprintProviderFactory(_id='sockarxiv', name='Sockarxiv')
        pp = PreprintFactory(finish=True, provider=provider)
        assert pp.url.startswith('/preprints/sockarxiv')

        res = self.app.get(pp.url + 'download')
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=1' in res.location

        res = self.app.get(pp.url + 'download/')
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=1' in res.location

    @mock.patch('website.settings.USE_EXTERNAL_EMBER', True)
    @mock.patch('website.settings.EXTERNAL_EMBER_APPS', {
        'preprints': {
            'server': 'http://localhost:4200',
            'path': '/preprints/'
        },
    })
    def test_resolve_guid_download_file_from_emberapp_preprints_unpublished(self):
        # non-branded domains
        provider = PreprintProviderFactory(_id='sockarxiv', name='Sockarxiv', reviews_workflow='pre-moderation')

        # branded domains
        branded_provider = PreprintProviderFactory(_id='spot', name='Spotarxiv', reviews_workflow='pre-moderation')
        branded_provider.allow_submissions = False
        branded_provider.domain = 'https://www.spotarxiv.com'
        branded_provider.description = 'spots not dots'
        branded_provider.domain_redirect_enabled = True
        branded_provider.share_publish_type = 'Thesis'
        branded_provider.save()

        # test_provider_submitter_can_download_unpublished
        submitter = AuthUserFactory()
        pp = PreprintFactory(finish=True, provider=provider, is_published=False, creator=submitter)
        pp.run_submit(submitter)
        pp_branded = PreprintFactory(finish=True, provider=branded_provider, is_published=False, filename='preprint_file_two.txt', creator=submitter)
        pp_branded.run_submit(submitter)

        res = self.app.get(f'{pp.url}download', auth=submitter.auth)
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=1' in res.location

        res = self.app.get(f'{pp_branded.url}download', auth=submitter.auth)
        assert res.status_code == 302

        # test_provider_super_user_can_download_unpublished
        super_user = AuthUserFactory()
        super_user.is_superuser = True
        super_user.save()

        res = self.app.get(f'{pp.url}download', auth=super_user.auth)
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=1' in res.location

        res = self.app.get(f'{pp_branded.url}download', auth=super_user.auth)
        assert res.status_code == 302

        # test_provider_moderator_can_download_unpublished
        moderator = AuthUserFactory()
        provider.add_to_group(moderator, 'moderator')
        provider.save()

        res = self.app.get(f'{pp.url}download', auth=moderator.auth)
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=1' in res.location

        branded_provider.add_to_group(moderator, 'moderator')
        branded_provider.save()

        res = self.app.get(f'{pp_branded.url}download', auth=moderator.auth)
        assert res.status_code == 302

        # test_provider_admin_can_download_unpublished
        admin = AuthUserFactory()
        provider.add_to_group(admin, ADMIN)
        provider.save()

        res = self.app.get(f'{pp.url}download', auth=admin.auth)
        assert res.status_code == 302
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?action=download&direct&version=1' in res.location

        branded_provider.add_to_group(admin, ADMIN)
        branded_provider.save()

        res = self.app.get(f'{pp_branded.url}download', auth=admin.auth)
        assert res.status_code == 302

    def test_resolve_guid_download_file_export(self):
        pp = PreprintFactory(finish=True)

        res = self.app.get(pp.url + 'download?format=asdf')
        assert res.status_code == 302
        assert f'{MFR_SERVER_URL}/export?format=asdf&url=' in res.location
        assert f'{quote(WATERBUTLER_URL)}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}%3Fformat%3Dasdf%26action%3Ddownload%26direct%26version%3D1' in res.location

        res = self.app.get(pp.url + 'download/?format=asdf')
        assert res.status_code == 302
        assert f'{MFR_SERVER_URL}/export?format=asdf&url=' in res.location
        assert f'{quote(WATERBUTLER_URL)}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}%3Fformat%3Dasdf%26action%3Ddownload%26direct%26version%3D1' in res.location

        res = self.app.get(f'/{pp.primary_file.get_guid(create=True)._id}/download?format=asdf')
        assert res.status_code == 302
        assert f'{MFR_SERVER_URL}/export?format=asdf&url=' in res.location

        assert f'{quote(WATERBUTLER_URL)}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}%3Fformat%3Dasdf%26action%3Ddownload%26direct%26version%3D1' in res.location

        res = self.app.get(f'/{pp.primary_file.get_guid(create=True)._id}/download/?format=asdf')
        assert res.status_code == 302
        assert f'{MFR_SERVER_URL}/export?format=asdf&url=' in res.location

        assert f'{quote(WATERBUTLER_URL)}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}%3Fformat%3Dasdf%26action%3Ddownload%26direct%26version%3D1' in res.location

        pp.primary_file.create_version(
            creator=pp.creator,
            location={'folder': 'osf', 'object': 'deadbe', 'service': 'cloud'},
            metadata={'contentType': 'img/png', 'size': 9001}
        )
        pp.primary_file.save()

        res = self.app.get(pp.url + 'download/?format=asdf')
        assert res.status_code == 302
        assert f'{MFR_SERVER_URL}/export?format=asdf&url=' in res.location
        assert f'{quote(WATERBUTLER_URL)}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}%3F' in res.location
        quarams = res.location.split('%3F')[1].split('%26')
        assert 'action%3Ddownload' in quarams
        assert 'version%3D2' in quarams
        assert 'direct' in quarams

        res = self.app.get(pp.url + 'download/?format=asdf&version=1')
        assert res.status_code == 302
        assert f'{MFR_SERVER_URL}/export?format=asdf&url=' in res.location
        assert f'{quote(WATERBUTLER_URL)}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}%3F' in res.location
        quarams = res.location.split('%3F')[1].split('%26')
        assert 'action%3Ddownload' in quarams
        assert 'version%3D1' in quarams
        assert 'direct' in quarams

        unpub_pp = PreprintFactory(project=self.node, is_published=False)
        res = self.app.get(unpub_pp.url + 'download?format=asdf', auth=unpub_pp.creator.auth)
        assert res.status_code == 302
        assert res.status_code == 302
        assert f'{MFR_SERVER_URL}/export?format=asdf&url=' in res.location
        assert f'{quote(WATERBUTLER_URL)}/v1/resources/{unpub_pp._id}/providers/{unpub_pp.primary_file.provider}{unpub_pp.primary_file.path}%3F' in res.location
        quarams = res.location.split('%3F')[1].split('%26')
        assert 'action%3Ddownload' in quarams
        assert 'version%3D1' in quarams
        assert 'direct' in quarams

    def test_resolve_guid_download_file_export_same_format_optimization(self):
        pp = PreprintFactory(filename='test.pdf', finish=True)

        res = self.app.get(pp.url + 'download/?format=pdf')
        assert res.status_code == 302
        assert f'{MFR_SERVER_URL}/export?' not in res.location
        assert f'{WATERBUTLER_URL}/v1/resources/{pp._id}/providers/{pp.primary_file.provider}{pp.primary_file.path}?format=pdf&action=download&direct&version=1' in res.location

    def test_resolve_guid_download_errors(self):
        testfile = TestFile.get_or_create(self.node, 'folder/path')
        testfile.name = 'asdf'
        testfile.materialized_path = '/folder/path'
        guid = testfile.get_guid(create=True)
        testfile.save()
        testfile.delete()
        res = self.app.get(f'/{guid}/download')
        assert res.status_code == 404

        pp = PreprintFactory(is_published=False)
        res = self.app.get(pp.url + 'download')
        assert res.status_code == 404

        pp.is_published = True
        pp.save()
        pp.is_public = False
        pp.save()

        non_contrib = AuthUserFactory()

        res = self.app.get(pp.url + 'download', auth=non_contrib.auth)
        assert res.status_code == 403

        pp.deleted = timezone.now()
        pp.save()

        res = self.app.get(pp.url + 'download', auth=non_contrib.auth)
        assert res.status_code == 410

@pytest.fixture()
def creator():
    return AuthUserFactory()

@pytest.fixture()
def auth(creator):
    return Auth(user=creator)

@pytest.fixture()
def preprint_provider():
    return PreprintProviderFactory()

@pytest.mark.django_db
class TestGuidVersionsThrough:
    def test_creation_versioned_guid(self, creator, preprint_provider):
        preprint = Preprint.create(
            creator=creator,
            provider=preprint_provider,
            title='Preprint',
            description='Abstract'
        )
        assert preprint.guids.count() == 1
        preprint_guid = preprint.guids.first()
        version_entry = preprint.versioned_guids.first()
        assert preprint.creator == creator
        assert preprint.provider == preprint_provider
        assert preprint.title == 'Preprint'
        assert preprint.description == 'Abstract'

        assert preprint_guid._id == version_entry.guid._id
        assert preprint_guid.referent == preprint
        assert preprint_guid.content_type.model == 'preprint'
        assert preprint_guid.object_id == preprint.pk
        assert preprint_guid.is_versioned is True

        assert version_entry.guid == preprint_guid
        assert version_entry.referent == preprint
        assert version_entry.content_type.model == 'preprint'
        assert version_entry.object_id == preprint.pk
        assert version_entry.version == 1

    def test_create_version(self, creator, preprint_provider):
        preprint = PreprintFactory(creator=creator)
        assert preprint.guids.count() == 1
        preprint_guid = preprint.guids.first()

        preprint_metadata = {
            'subjects': [[el] for el in preprint.subjects.all().values_list('_id', flat=True)],
            'original_publication_date': preprint.original_publication_date,
            'custom_publication_citation': preprint.custom_publication_citation,
            'article_doi': preprint.article_doi,
            'has_coi': preprint.has_coi,
            'conflict_of_interest_statement': preprint.conflict_of_interest_statement,
            'has_data_links': preprint.has_data_links,
            'why_no_data': preprint.why_no_data,
            'data_links': preprint.data_links,
            'has_prereg_links': preprint.has_prereg_links,
            'why_no_prereg': preprint.why_no_prereg,
            'prereg_links': preprint.prereg_links,
        }
        if preprint.node:
            preprint_metadata['node'] = preprint.node
        if preprint.license:
            preprint_metadata['license_type'] = preprint.license.node_license
            preprint_metadata['license'] = {
                'copyright_holders': preprint.license.copyright_holders,
                'year': preprint.license.year
            }

        auth = Auth(user=creator)
        new_preprint, data_for_update = Preprint.create_version(
            create_from_guid=preprint._id,
            auth=auth
        )
        tags = data_for_update.pop('tags')
        assert list(tags) == list(preprint.tags.all().values_list('name', flat=True))
        assert preprint_metadata == data_for_update

        new_version = new_preprint.versioned_guids.first()

        assert preprint.guids.count() == 0
        assert preprint.versioned_guids.count() == 1
        assert preprint.files.count() == 1
        assert new_preprint.guids.count() == 1
        assert new_preprint.versioned_guids.count() == 1
        assert new_preprint.files.count() == 0

        assert new_version.referent == new_preprint
        assert new_version.object_id == new_preprint.pk
        assert new_version.content_type.model == 'preprint'
        assert new_version.guid == preprint_guid
        assert new_version.version == 2
        assert preprint_guid.versions.count() == 2

    def test_versioned_preprint_id_property(self, creator, preprint_provider):
        preprint = Preprint.create(
            creator=creator,
            provider=preprint_provider,
            title='Preprint',
            description='Abstract'
        )
        preprint_guid = preprint.guids.first()
        expected_guid = f'{preprint_guid._id}{VersionedGuidMixin.GUID_VERSION_DELIMITER}1'

        assert preprint._id == expected_guid

        GuidVersionsThrough.objects.filter(guid=preprint_guid).delete()

        assert preprint._id is None
