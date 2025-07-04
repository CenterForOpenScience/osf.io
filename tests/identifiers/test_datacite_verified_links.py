import pytest
from unittest import mock

from osf.metadata.serializers.datacite.datacite_tree_walker import DataciteTreeWalker
from osf.metadata import gather

from osf_tests.factories import NodeFactory, UserFactory


@pytest.mark.django_db
class TestDataCiteVerifiedLinks:

    @pytest.fixture
    def node(self):
        return NodeFactory(is_public=True)

    @pytest.fixture
    def basket(self, node):
        from osf.metadata.osf_gathering import OsfFocus
        focus = OsfFocus(node)
        return gather.Basket(focus)

    @pytest.fixture
    def tree_walker(self, basket):
        def mock_visit(parent, tag, text=None, attrib=None, is_list=False):
            element = {'tag': tag, 'text': text, 'attrib': attrib or {}}
            if is_list:
                element['children'] = []
            return element

        walker = DataciteTreeWalker(basket, None, mock_visit)
        walker.visit = mock_visit
        return walker

    @mock.patch('framework.sentry.log_message')
    def test_valid_verified_links(self, mock_sentry_log, tree_walker, mock_gravy_valet_get_verified_links):
        mock_gravy_valet_get_verified_links.return_value = [
            {'target_url': 'https://example.com/dataset', 'resource_type': 'Dataset'},
            {'target_url': 'https://github.com/user/repo', 'resource_type': 'Software'},
            {'target_url': 'https://osf.io/abc123/', 'resource_type': 'Text'}
        ]

        parent_el = {'tag': 'resource', 'children': []}

        tree_walker._visit_related_and_verified_links(parent_el)

        mock_gravy_valet_get_verified_links.assert_called_once_with(tree_walker.basket.focus.dbmodel._id)

        mock_sentry_log.assert_not_called()

    @mock.patch('framework.sentry.log_message')
    def test_missing_target_url(self, mock_sentry_log, tree_walker, mock_gravy_valet_get_verified_links):
        mock_gravy_valet_get_verified_links.return_value = [
            {'resource_type': 'Dataset'},
            {'target_url': 'https://example.com/valid', 'resource_type': 'Software'}  # Valid link
        ]

        parent_el = {'tag': 'resource', 'children': []}
        tree_walker._visit_related_and_verified_links(parent_el)

        mock_sentry_log.assert_called_once()
        call_args = mock_sentry_log.call_args[0]
        assert 'Skipped items for node' in call_args[0]
        assert 'Missing data: [link=None, type=Dataset]' in call_args[0]

    @mock.patch('framework.sentry.log_message')
    def test_missing_resource_type(self, mock_sentry_log, tree_walker, mock_gravy_valet_get_verified_links):
        mock_gravy_valet_get_verified_links.return_value = [
            {'target_url': 'https://example.com/dataset'},  # Missing resource_type
            {'target_url': 'https://example.com/valid', 'resource_type': 'Software'}  # Valid link
        ]

        parent_el = {'tag': 'resource', 'children': []}
        tree_walker._visit_related_and_verified_links(parent_el)

        mock_sentry_log.assert_called_once()
        call_args = mock_sentry_log.call_args[0]
        assert 'Skipped items for node' in call_args[0]
        assert 'Missing data: [link=https://example.com/dataset, type=None]' in call_args[0]

    @mock.patch('framework.sentry.log_message')
    def test_invalid_url_format(self, mock_sentry_log, tree_walker, mock_gravy_valet_get_verified_links):
        mock_gravy_valet_get_verified_links.return_value = [
            {'target_url': 'not-a-valid-url', 'resource_type': 'Dataset'},
            {'target_url': 'also.invalid', 'resource_type': 'Software'},
            {'target_url': 'https://example.com/valid', 'resource_type': 'Text'}
        ]

        parent_el = {'tag': 'resource', 'children': []}
        tree_walker._visit_related_and_verified_links(parent_el)

        mock_sentry_log.assert_called_once()
        call_args = mock_sentry_log.call_args[0]
        assert 'Skipped items for node' in call_args[0]
        assert 'Invalid link: [link=not-a-valid-url, type=Dataset]' in call_args[0]
        assert 'Invalid link: [link=also.invalid, type=Software]' in call_args[0]

    @mock.patch('framework.sentry.log_message')
    def test_multiple_issues_combined(self, mock_sentry_log, tree_walker, mock_gravy_valet_get_verified_links):
        mock_gravy_valet_get_verified_links.return_value = [
            {'resource_type': 'Dataset'},
            {'target_url': 'invalid-url', 'resource_type': 'Software'},
            {'target_url': 'https://example.com/missing-type'},
            {'target_url': 'https://example.com/valid', 'resource_type': 'Text'}
        ]

        parent_el = {'tag': 'resource', 'children': []}
        tree_walker._visit_related_and_verified_links(parent_el)

        mock_sentry_log.assert_called_once()
        call_args = mock_sentry_log.call_args[0]
        log_message = call_args[0]

        assert 'Skipped items for node' in log_message
        assert 'Missing data: [link=None, type=Dataset]' in log_message
        assert 'Invalid link: [link=invalid-url, type=Software]' in log_message
        assert 'Missing data: [link=https://example.com/missing-type, type=None]' in log_message

    @mock.patch('framework.sentry.log_message')
    def test_empty_verified_links(self, mock_sentry_log, tree_walker, mock_gravy_valet_get_verified_links):
        mock_gravy_valet_get_verified_links.return_value = []

        parent_el = {'tag': 'resource', 'children': []}
        tree_walker._visit_related_and_verified_links(parent_el)

        mock_gravy_valet_get_verified_links.assert_called_once()

        mock_sentry_log.assert_not_called()

    @mock.patch('framework.sentry.log_message')
    def test_resource_type_title_case(self, mock_sentry_log, tree_walker, mock_gravy_valet_get_verified_links):
        mock_gravy_valet_get_verified_links.return_value = [
            {'target_url': 'https://example.com/dataset', 'resource_type': 'Dataset'},
            {'target_url': 'https://example.com/software', 'resource_type': 'Software'},
            {'target_url': 'https://example.com/text', 'resource_type': 'Text'}
        ]

        parent_el = {'tag': 'resource', 'children': []}

        visit_calls = []
        original_visit = tree_walker.visit

        def capture_visit(*args, **kwargs):
            visit_calls.append((args, kwargs))
            return original_visit(*args, **kwargs)

        tree_walker.visit = capture_visit
        tree_walker._visit_related_and_verified_links(parent_el)

        related_identifier_calls = [
            call for call in visit_calls
            if len(call[0]) >= 2 and call[0][1] == 'relatedIdentifier'
        ]

        assert len(related_identifier_calls) == 3

        resource_types = [call[1]['attrib']['resourceTypeGeneral'] for call in related_identifier_calls]
        assert 'Dataset' in resource_types
        assert 'Software' in resource_types
        assert 'Text' in resource_types

    def test_non_abstract_node_skipped(self, tree_walker, mock_gravy_valet_get_verified_links):
        from osf.metadata.osf_gathering import OsfFocus
        user = UserFactory()
        focus = OsfFocus(user)
        tree_walker.basket = gather.Basket(focus)

        parent_el = {'tag': 'resource', 'children': []}
        tree_walker._visit_related_and_verified_links(parent_el)

        mock_gravy_valet_get_verified_links.assert_not_called()

    @mock.patch('framework.sentry.log_message')
    def test_edge_case_empty_strings(self, mock_sentry_log, tree_walker, mock_gravy_valet_get_verified_links):
        mock_gravy_valet_get_verified_links.return_value = [
            {'target_url': '', 'resource_type': 'Dataset'},
            {'target_url': 'https://example.com/valid', 'resource_type': ''},
            {'target_url': 'https://example.com/valid2', 'resource_type': 'Software'}
        ]

        parent_el = {'tag': 'resource', 'children': []}
        tree_walker._visit_related_and_verified_links(parent_el)

        mock_sentry_log.assert_called_once()
        call_args = mock_sentry_log.call_args[0]
        log_message = call_args[0]

        assert 'Missing data: [link=, type=Dataset]' in log_message
        assert 'Missing data: [link=https://example.com/valid, type=]' in log_message

    @mock.patch('framework.sentry.log_message')
    def test_url_validation_edge_cases(self, mock_sentry_log, tree_walker, mock_gravy_valet_get_verified_links):
        mock_gravy_valet_get_verified_links.return_value = [
            {'target_url': 'http://example.com', 'resource_type': 'Dataset'},
            {'target_url': 'https://example.com', 'resource_type': 'Software'},
            {'target_url': 'ftp://example.com/file', 'resource_type': 'Text'},
            {'target_url': 'example.com', 'resource_type': 'Dataset'},
            {'target_url': 'www.example.com', 'resource_type': 'Software'},
        ]

        parent_el = {'tag': 'resource', 'children': []}
        tree_walker._visit_related_and_verified_links(parent_el)

        mock_sentry_log.assert_called_once()
        call_args = mock_sentry_log.call_args[0]
        log_message = call_args[0]

        assert 'Invalid link: [link=example.com, type=Dataset]' in log_message
        assert 'Invalid link: [link=www.example.com, type=Software]' in log_message