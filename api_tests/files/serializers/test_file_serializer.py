from datetime import datetime

import pytest
from pytz import utc

from addons.base.utils import get_mfr_url
from api.files.serializers import FileSerializer
from api_tests import utils
from osf_tests.factories import (
    UserFactory,
    PreprintFactory,
    NodeFactory,
)
from tests.utils import make_drf_request_with_version

@pytest.fixture()
def user():
    return UserFactory()


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

    def test_file_serializer(self, file_one):
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

    def test_serialize_preprint_file(self, preprint, primary_file):
        req = make_drf_request_with_version(version='2.2')
        data = FileSerializer(primary_file, context={'request': req}).data['data']
        download_link = data['links']['download']
        render_link = data['links']['render']
        mfr_url = get_mfr_url(preprint, 'osfstorage')

        assert download_link in render_link
        # Check render file link with path
        assert render_link == mfr_url + '/render?url=' + download_link + '?direct%26mode=render'

        # Check render file link with guid
        primary_file.get_guid(create=True)._id
        req = make_drf_request_with_version()
        data = FileSerializer(primary_file, context={'request': req}).data['data']
        download_link = data['links']['download']
        render_link = data['links']['render']
        assert render_link == mfr_url + '/render?url=' + download_link + '?direct%26mode=render'

    def test_no_node_relationship_after_version_2_7(self, file_one):
        req_2_7 = make_drf_request_with_version(version='2.7')
        data_2_7 = FileSerializer(file_one, context={'request': req_2_7}).data['data']
        assert 'node' in data_2_7['relationships'].keys()

        req_2_8 = make_drf_request_with_version(version='2.8')
        data_2_8 = FileSerializer(file_one, context={'request': req_2_8}).data['data']
        assert 'node' not in data_2_8['relationships'].keys()
