import mock
import pytest
import urllib
from django.core.exceptions import MultipleObjectsReturned

from osf.models import Guid, NodeLicenseRecord, OSFUser
from osf_tests.factories import AuthUserFactory, UserFactory, NodeFactory, NodeLicenseRecordFactory, \
    RegistrationFactory, PreprintFactory, PreprintProviderFactory
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
            pytest.fail('Multiple objects returned for {} with multiple guids. {}'.format(Factory._meta.model, ex))


class TestResolveGuid(OsfTestCase):

    def setUp(self):
        super(TestResolveGuid, self).setUp()
        self.node = NodeFactory()

    def test_resolve_guid(self):
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
            expect_errors=True,
        )
        assert res.status_code == 404

    @mock.patch('osf.models.node.Node.deep_url', None)
    def test_resolve_guid_no_url(self):
        res = self.app.get(
            self.node.web_url_for('node_setting', _guid=True),
            auth=self.node.creator.auth,
            expect_errors=True,
        )
        assert res.status_code == 404

    def test_resolve_guid_download_file(self):
        pp = PreprintFactory(finish=True)

        res = self.app.get(pp.url + 'download')
        assert res.status_code == 302
        assert '{}/v1/resources/{}/providers/{}{}?action=download&version=1&direct'.format(WATERBUTLER_URL, pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        res = self.app.get(pp.url + 'download/')
        assert res.status_code == 302
        assert '{}/v1/resources/{}/providers/{}{}?action=download&version=1&direct'.format(WATERBUTLER_URL, pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        res = self.app.get('/{}/download'.format(pp.primary_file.get_guid(create=True)._id))
        assert res.status_code == 302
        assert '{}/v1/resources/{}/providers/{}{}?action=download&version=1&direct'.format(WATERBUTLER_URL, pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        pp.primary_file.create_version(
            creator=pp.node.creator,
            location={u'folder': u'osf', u'object': u'deadbe', u'service': u'cloud'},
            metadata={u'contentType': u'img/png', u'size': 9001}
        )
        pp.primary_file.save()

        res = self.app.get(pp.url + 'download/')
        assert res.status_code == 302
        assert '{}/v1/resources/{}/providers/{}{}?action=download&version=2&direct'.format(WATERBUTLER_URL, pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        res = self.app.get(pp.url + 'download/?version=1')
        assert res.status_code == 302
        assert '{}/v1/resources/{}/providers/{}{}?action=download&version=1&direct'.format(WATERBUTLER_URL, pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        unpub_pp = PreprintFactory(project=self.node, is_published=False)
        res = self.app.get(unpub_pp.url + 'download/?version=1', auth=self.node.creator.auth)
        assert res.status_code == 302
        assert '{}/v1/resources/{}/providers/{}{}?action=download&version=1&direct'.format(WATERBUTLER_URL, unpub_pp.node._id, unpub_pp.primary_file.provider, unpub_pp.primary_file.path) in res.location

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
        assert '{}/v1/resources/{}/providers/{}{}?action=download&version=1&direct'.format(WATERBUTLER_URL, pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        res = self.app.get(pp.url + 'download/')
        assert res.status_code == 302
        assert '{}/v1/resources/{}/providers/{}{}?action=download&version=1&direct'.format(WATERBUTLER_URL, pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

    def test_resolve_guid_download_file_export(self):
        pp = PreprintFactory(finish=True)

        res = self.app.get(pp.url + 'download?format=asdf')
        assert res.status_code == 302
        assert '{}/export?format=asdf&url='.format(MFR_SERVER_URL) in res.location
        assert '{}/v1/resources/{}/providers/{}{}%3Faction%3Ddownload'.format(urllib.quote(WATERBUTLER_URL), pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        res = self.app.get(pp.url + 'download/?format=asdf')
        assert res.status_code == 302
        assert '{}/export?format=asdf&url='.format(MFR_SERVER_URL) in res.location
        assert '{}/v1/resources/{}/providers/{}{}%3Faction%3Ddownload'.format(urllib.quote(WATERBUTLER_URL), pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        res = self.app.get('/{}/download?format=asdf'.format(pp.primary_file.get_guid(create=True)._id))
        assert res.status_code == 302
        assert '{}/export?format=asdf&url='.format(MFR_SERVER_URL) in res.location
        assert '{}/v1/resources/{}/providers/{}{}%3Faction%3Ddownload'.format(urllib.quote(WATERBUTLER_URL), pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        res = self.app.get('/{}/download/?format=asdf'.format(pp.primary_file.get_guid(create=True)._id))
        assert res.status_code == 302
        assert '{}/export?format=asdf&url='.format(MFR_SERVER_URL) in res.location
        assert '{}/v1/resources/{}/providers/{}{}%3Faction%3Ddownload'.format(urllib.quote(WATERBUTLER_URL), pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

        pp.primary_file.create_version(
            creator=pp.node.creator,
            location={u'folder': u'osf', u'object': u'deadbe', u'service': u'cloud'},
            metadata={u'contentType': u'img/png', u'size': 9001}
        )
        pp.primary_file.save()

        res = self.app.get(pp.url + 'download/?format=asdf')
        assert res.status_code == 302
        assert '{}/export?format=asdf&url='.format(MFR_SERVER_URL) in res.location
        assert '{}/v1/resources/{}/providers/{}{}%3F'.format(urllib.quote(WATERBUTLER_URL), pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location
        quarams = res.location.split('%3F')[1].split('%26')
        assert 'action%3Ddownload' in quarams
        assert 'version%3D2' in quarams
        assert 'direct' in quarams

        res = self.app.get(pp.url + 'download/?format=asdf&version=1')
        assert res.status_code == 302
        assert '{}/export?format=asdf&url='.format(MFR_SERVER_URL) in res.location
        assert '{}/v1/resources/{}/providers/{}{}%3F'.format(urllib.quote(WATERBUTLER_URL), pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location
        quarams = res.location.split('%3F')[1].split('%26')
        assert 'action%3Ddownload' in quarams
        assert 'version%3D1' in quarams
        assert 'direct' in quarams

        unpub_pp = PreprintFactory(project=self.node, is_published=False)
        res = self.app.get(unpub_pp.url + 'download?format=asdf', auth=unpub_pp.node.creator.auth)
        assert res.status_code == 302
        assert res.status_code == 302
        assert '{}/export?format=asdf&url='.format(MFR_SERVER_URL) in res.location
        assert '{}/v1/resources/{}/providers/{}{}%3F'.format(urllib.quote(WATERBUTLER_URL), unpub_pp.node._id, unpub_pp.primary_file.provider, unpub_pp.primary_file.path) in res.location
        quarams = res.location.split('%3F')[1].split('%26')
        assert 'action%3Ddownload' in quarams
        assert 'version%3D1' in quarams
        assert 'direct' in quarams

    def test_resolve_guid_download_file_export_same_format_optimization(self):
        pp = PreprintFactory(filename='test.pdf', finish=True)

        res = self.app.get(pp.url + 'download/?format=pdf')
        assert res.status_code == 302
        assert '{}/export?'.format(MFR_SERVER_URL) not in res.location
        assert '{}/v1/resources/{}/providers/{}{}?action=download&version=1&direct'.format(WATERBUTLER_URL, pp.node._id, pp.primary_file.provider, pp.primary_file.path) in res.location

    def test_resolve_guid_download_errors(self):
        testfile = TestFile.get_or_create(self.node, 'folder/path')
        testfile.name = 'asdf'
        testfile.materialized_path = '/folder/path'
        guid = testfile.get_guid(create=True)
        testfile.save()
        testfile.delete()
        res = self.app.get('/{}/download'.format(guid), expect_errors=True)
        assert res.status_code == 404

        pp = PreprintFactory(is_published=False)

        res = self.app.get(pp.url + 'download', expect_errors=True)
        assert res.status_code == 404

        pp.is_published = True
        pp.save()
        pp.node.is_public = False
        pp.node.save()

        non_contrib = AuthUserFactory()

        res = self.app.get(pp.url + 'download', auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        pp.node.is_deleted = True
        pp.node.save()

        res = self.app.get(pp.url + 'download', auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 410
