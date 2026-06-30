from unittest import mock

import pytest

from api.share import utils as share_utils
from osf.metadata.osf_gathering import OsfmapPartition
from osf_tests.factories import ProjectFactory
from website import settings


@pytest.mark.django_db
class TestShareRequestTimeout:

    @pytest.fixture()
    def public_node(self):
        return ProjectFactory(is_public=True)

    def test_delete_trove_record_passes_timeout(self, public_node):
        with mock.patch.object(share_utils.requests, 'delete') as mock_delete:
            share_utils.pls_delete_trove_record(public_node, osfmap_partition=OsfmapPartition.MAIN)
        assert mock_delete.call_args.kwargs['timeout'] == settings.EXTERNAL_REQUEST_TIMEOUT

    def test_send_trove_record_passes_timeout(self, public_node):
        fake_serializer = mock.Mock(mediatype='text/turtle')
        fake_serializer.serialize.return_value = b'<turtle>'
        with (
            mock.patch.object(share_utils, 'pls_get_magic_metadata_basket'),
            mock.patch.object(share_utils, 'get_metadata_serializer', return_value=fake_serializer),
            mock.patch.object(share_utils.requests, 'post') as mock_post,
        ):
            share_utils.pls_send_trove_record(
                public_node,
                is_backfill=False,
                osfmap_partition=OsfmapPartition.MAIN,
            )
        assert mock_post.call_args.kwargs['timeout'] == settings.EXTERNAL_REQUEST_TIMEOUT
