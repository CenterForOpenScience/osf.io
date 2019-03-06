from datetime import datetime

import pytest
from pytz import utc

from addons.base.utils import get_mfr_url
from api.files.serializers import FileSerializer, get_file_download_link, get_file_render_link
from api_tests import utils
from osf_tests.factories import (
    UserFactory,
    PreprintFactory,
    NodeFactory,
)
from tests.utils import make_drf_request_with_version
from website import settings

@pytest.fixture()
def user():
    return UserFactory()

def build_expected_render_link(mfr_url, download_url, with_version=True):
    if with_version:
        return '{}/render?url={}%26direct%26mode=render'.format(mfr_url, download_url)
    else:
        return '{}/render?url={}?direct%26mode=render'.format(mfr_url, download_url)


@pytest.mark.django_db
class TestFileSerializer:

    @pytest.fixture()
    def node(self, user):
        return NodeFactory(creator=user)

    @pytest.fixture()
    def file_one(self, node, user):
        return utils.create_test_file(node, user, create_guid=False)

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture()
    def primary_file(self, preprint):
        return preprint.primary_file

    def test_file_serializer(self, file_one, node):
        created = file_one.versions.last().created
        modified = file_one.versions.first().created
        created_tz_aware = created.replace(tzinfo=utc)
        modified_tz_aware = modified.replace(tzinfo=utc)
        new_format = '%Y-%m-%dT%H:%M:%S.%fZ'

        download_base = '/download/{}'
        path = file_one._id
        mfr_url = get_mfr_url(file_one, 'osfstorage')

        # test_date_modified_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        data = FileSerializer(file_one, context={'request': req}).data['data']
        assert modified_tz_aware == data['attributes']['date_modified']

        # test_date_modified_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(file_one, context={'request': req}).data['data']
        assert datetime.strftime(
            modified, new_format
        ) == data['attributes']['date_modified']

        # test_date_created_formats_to_old_format
        req = make_drf_request_with_version(version='2.0')
        data = FileSerializer(file_one, context={'request': req}).data['data']
        assert created_tz_aware == data['attributes']['date_created']

        # test_date_created_formats_to_new_format
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(file_one, context={'request': req}).data['data']
        assert datetime.strftime(
            created, new_format
        ) == data['attributes']['date_created']

        # check download file link with path
        assert download_base.format(path) in data['links']['download']

        # check render file link with path
        assert download_base.format(path) in data['links']['render']
        assert mfr_url in data['links']['render']

        # check download file link with guid
        guid = file_one.get_guid(create=True)._id
        req = make_drf_request_with_version()
        data = FileSerializer(file_one, context={'request': req}).data['data']
        assert download_base.format(guid) in data['links']['download']

        # check render file link with guid
        assert download_base.format(guid) in data['links']['render']
        assert mfr_url in data['links']['render']

        # check html link in file serializer
        assert data['links']['html'] == '{}{}/files/osfstorage/{}'.format(settings.DOMAIN, node._id, file_one._id)

        # check download/render/html link for folder
        folder = node.get_addon('osfstorage').get_root().append_folder('Test_folder')
        folder.save()
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(folder, context={'request': req}).data['data']
        assert 'render' not in data['links']
        assert 'download' not in data['links']
        assert 'html' not in data['links']

    def test_serialize_preprint_file(self, preprint, primary_file):
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(primary_file, context={'request': req}).data['data']
        mfr_url = get_mfr_url(preprint, 'osfstorage')

        # Check render file link with path
        download_link = data['links']['download']
        assert data['links']['render'] == build_expected_render_link(mfr_url, download_link, with_version=False)

        # Check render file link with guid
        primary_file.get_guid(create=True)._id
        req = make_drf_request_with_version()
        data = FileSerializer(primary_file, context={'request': req}).data['data']
        download_link = data['links']['download']
        assert data['links']['render'] == build_expected_render_link(mfr_url, download_link, with_version=False)

        # Check html link
        assert data['links']['html'] == '{}{}/files/osfstorage/{}'.format(settings.DOMAIN, preprint._id, primary_file._id)

    def test_get_file_download_and_render_links(self, file_one, node):
        mfr_link = get_mfr_url(file_one.target, 'osfstorage')

        # file links with path
        download_link = get_file_download_link(file_one)
        assert download_link == '{}download/{}/'.format(settings.DOMAIN, file_one._id)
        assert get_file_render_link(mfr_link, download_link) == build_expected_render_link(mfr_link, download_link, with_version=False)

        # file versions link with path
        download_link = get_file_download_link(file_one, version=2)
        assert download_link == '{}download/{}/?revision=2'.format(settings.DOMAIN, file_one._id)
        assert get_file_render_link(mfr_link, download_link, version=2) == build_expected_render_link(mfr_link, download_link)

        # file links with guid
        file_one.get_guid(create=True)
        download_link = get_file_download_link(file_one)
        assert download_link == '{}download/{}/'.format(settings.DOMAIN, file_one.get_guid()._id)
        assert get_file_render_link(mfr_link, download_link) == build_expected_render_link(mfr_link, download_link, with_version=False)

        # file version links with guid
        download_link = get_file_download_link(file_one, version=2)
        assert download_link == '{}download/{}/?revision=2'.format(settings.DOMAIN, file_one.get_guid()._id)
        assert get_file_render_link(mfr_link, download_link, version=2) == build_expected_render_link(mfr_link, download_link)

    def test_no_node_relationship_after_version_2_7(self, file_one):
        req_2_7 = make_drf_request_with_version(version='2.7')
        data_2_7 = FileSerializer(file_one, context={'request': req_2_7}).data['data']
        assert 'node' in data_2_7['relationships'].keys()

        req_2_8 = make_drf_request_with_version(version='2.8')
        data_2_8 = FileSerializer(file_one, context={'request': req_2_8}).data['data']
        assert 'node' not in data_2_8['relationships'].keys()
