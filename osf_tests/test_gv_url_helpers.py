import pytest
from unittest.mock import patch

from osf.models import Node, OSFUser
from osf_tests.factories import ProjectFactory, UserFactory
from osf.tasks import get_object_by_url


@pytest.mark.django_db
class TestGVURLHelpers:

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    def test_get_object_by_url_valid_node(self, node):
        url = f"http://localhost:5000/{node._id}/"
        result = get_object_by_url(url, Node)
        assert result == node

    def test_get_object_by_url_valid_user(self, user):
        url = f"http://localhost:5000/{user._id}/"
        result = get_object_by_url(url, OSFUser)
        assert result == user

    def test_get_object_by_url_invalid_id(self):
        url = 'http://localhost:5000/xxxxx/'
        result = get_object_by_url(url, Node)
        assert result is None

    def test_get_object_by_url_nonexistent_object(self):
        url = 'http://localhost:5000/aaaaa/'
        result = get_object_by_url(url, Node)
        assert result is None

    def test_get_object_by_url_invalid_url(self):
        invalid_urls = [
            'http://localhost:5000/',
            'http://localhost:5000/too/many/segments/',
            'not-a-url',
            'http://localhost:5000/toolong/',
        ]

        for url in invalid_urls:
            result = get_object_by_url(url, Node)
            assert result is None

    @patch('osf.tasks.log_message')
    def test_get_object_by_url_logs_error(self, mock_log_message):
        url = 'invalid-url'
        get_object_by_url(url, Node)
        mock_log_message.assert_called_once()

        mock_log_message.reset_mock()

        url = 'http://localhost:5000/aaaaa/'
        get_object_by_url(url, Node)
        mock_log_message.assert_called_once()
