import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from waffle.testutils import override_flag
from osf.external.gravy_valet import translations as gv_translations
from osf.external.gravy_valet import request_helpers as gv_requests
from osf_tests.factories import ProjectFactory, UserFactory
from osf import features
from framework.auth import Auth


@pytest.mark.django_db
class TestGVSessionOptimization:

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def mock_request(self):
        mock_request = MagicMock()
        return mock_request

    @pytest.fixture()
    def mock_external_service(self):
        mock_external_service = MagicMock()
        mock_external_service.short_name = 'github'
        mock_external_service.type = 'storage'
        return mock_external_service

    @pytest.fixture()
    def mock_addon(self):
        mock_addon = MagicMock()
        mock_addon.short_name = 'github'
        return mock_addon

    @patch('osf.models.node.get_current_request')
    @patch('api.waffle.utils.flag_is_active')
    @patch('osf.models.node.OSFUser.load')
    @patch('osf.external.gravy_valet.translations.get_external_services')
    @patch('osf.models.node.AbstractNode._get_addons_from_gv')
    @patch('osf.features.ENABLE_GV', True)
    def test_get_addon_from_gv_caches_addons(
        self, mock_get_addons, mock_get_services, mock_load_user, mock_flag, mock_get_request,
        node, user, mock_request, mock_external_service, mock_addon
    ):
        mock_get_request.return_value = mock_request
        mock_flag.return_value = True
        mock_load_user.return_value = user
        mock_get_services.return_value = [mock_external_service]
        mock_get_addons.return_value = [mock_addon]

        # Make sure request.gv_addons is not set yet
        if hasattr(mock_request, 'gv_addons'):
            delattr(mock_request, 'gv_addons')

        original_method = node._get_addon_from_gv

        def mock_get_addon_from_gv(self, gv_pk, requesting_user_id, auth=None):
            request = mock_get_request()
            # This is to avoid making multiple requests to GV
            # within the lifespan of one request on the OSF side
            try:
                gv_addons = request.gv_addons
            except AttributeError:
                mock_load_user(requesting_user_id)
                services = mock_get_services(user)
                for service in services:
                    if service.short_name == gv_pk:
                        break
                else:
                    return None
                request.gv_addons = mock_get_addons(requesting_user_id, service.type, auth=auth)
                gv_addons = request.gv_addons

            for item in gv_addons:
                if item.short_name == gv_pk:
                    return item
            return None

        from types import MethodType
        node._get_addon_from_gv = MethodType(mock_get_addon_from_gv, node)

        try:
            result = node._get_addon_from_gv('github', user._id)

            assert result == mock_addon
            assert hasattr(mock_request, 'gv_addons')
            assert mock_request.gv_addons == [mock_addon]
            mock_get_services.assert_called_once_with(user)
            mock_get_addons.assert_called_once_with(user._id, mock_external_service.type, auth=None)

            mock_get_services.reset_mock()
            mock_get_addons.reset_mock()
            mock_load_user.reset_mock()

            result2 = node._get_addon_from_gv('github', user._id)

            assert result2 == mock_addon
            mock_get_services.assert_not_called()
            mock_get_addons.assert_not_called()
            mock_load_user.assert_not_called()
        finally:
            node._get_addon_from_gv = original_method

    @patch('osf.models.node.get_current_request')
    @patch('api.waffle.utils.flag_is_active')
    @patch('osf.models.node.OSFUser.load')
    @patch('osf.external.gravy_valet.translations.get_external_services')
    @patch('osf.models.node.AbstractNode._get_addons_from_gv')
    @patch('osf.features.ENABLE_GV', True)
    def test_get_addon_from_gv_not_found(
        self, mock_get_addons, mock_get_services, mock_load_user, mock_flag, mock_get_request,
        node, user, mock_request, mock_external_service
    ):
        mock_get_request.return_value = mock_request
        mock_flag.return_value = True
        mock_load_user.return_value = user
        mock_get_services.return_value = [mock_external_service]  # github
        mock_get_addons.return_value = []  # No addons returned

        # Make sure request.gv_addons is not set yet
        if hasattr(mock_request, 'gv_addons'):
            delattr(mock_request, 'gv_addons')

        original_method = node._get_addon_from_gv

        def mock_get_addon_from_gv(self, gv_pk, requesting_user_id, auth=None):
            request = mock_get_request()
            # This is to avoid making multiple requests to GV
            # within the lifespan of one request on the OSF side
            try:
                gv_addons = request.gv_addons
            except AttributeError:
                mock_load_user(requesting_user_id)
                services = mock_get_services(user)
                for service in services:
                    if service.short_name == gv_pk:
                        break
                else:
                    return None
                request.gv_addons = mock_get_addons(requesting_user_id, service.type, auth=auth)
                gv_addons = request.gv_addons

            for item in gv_addons:
                if item.short_name == gv_pk:
                    return item
            return None

        from types import MethodType
        node._get_addon_from_gv = MethodType(mock_get_addon_from_gv, node)

        try:
            result = node._get_addon_from_gv('github', user._id)

            assert result is None
            mock_get_services.assert_called_once_with(user)
            mock_get_addons.assert_called_once_with(user._id, mock_external_service.type, auth=None)
        finally:
            node._get_addon_from_gv = original_method

    @patch('osf.models.node.get_current_request')
    @patch('api.waffle.utils.flag_is_active')
    @patch('osf.models.node.OSFUser.load')
    @patch('osf.external.gravy_valet.translations.get_external_services')
    @patch('osf.models.node.AbstractNode._get_addons_from_gv')
    @patch('osf.features.ENABLE_GV', True)
    def test_get_addon_from_gv_multiple_addons(
        self, mock_get_addons, mock_get_services, mock_load_user, mock_flag, mock_get_request,
        node, user, mock_request, mock_external_service
    ):
        mock_get_request.return_value = mock_request
        mock_flag.return_value = True
        mock_load_user.return_value = user
        mock_get_services.return_value = [mock_external_service]  # github service

        mock_addon1 = MagicMock()
        mock_addon1.short_name = 'github'
        mock_addon2 = MagicMock()
        mock_addon2.short_name = 'figshare'
        mock_get_addons.return_value = [mock_addon1, mock_addon2]

        # Make sure request.gv_addons is not set yet
        if hasattr(mock_request, 'gv_addons'):
            delattr(mock_request, 'gv_addons')

        original_method = node._get_addon_from_gv

        def mock_get_addon_from_gv(self, gv_pk, requesting_user_id, auth=None):
            request = mock_get_request()
            # This is to avoid making multiple requests to GV
            # within the lifespan of one request on the OSF side
            try:
                gv_addons = request.gv_addons
            except AttributeError:
                mock_load_user(requesting_user_id)
                services = mock_get_services(user)
                for service in services:
                    if service.short_name == gv_pk:
                        break
                else:
                    return None
                request.gv_addons = mock_get_addons(requesting_user_id, service.type, auth=auth)
                gv_addons = request.gv_addons

            for item in gv_addons:
                if item.short_name == gv_pk:
                    return item
            return None

        from types import MethodType
        node._get_addon_from_gv = MethodType(mock_get_addon_from_gv, node)

        try:
            result1 = node._get_addon_from_gv('github', user._id)

            assert result1 == mock_addon1
            assert hasattr(mock_request, 'gv_addons')
            assert mock_request.gv_addons == [mock_addon1, mock_addon2]
            mock_get_services.assert_called_once_with(user)
            mock_get_addons.assert_called_once_with(user._id, mock_external_service.type, auth=None)

            mock_get_services.reset_mock()
            mock_get_addons.reset_mock()
            mock_load_user.reset_mock()

            result2 = node._get_addon_from_gv('figshare', user._id)

            assert result2 == mock_addon2
            mock_get_services.assert_not_called()
            mock_get_addons.assert_not_called()
            mock_load_user.assert_not_called()
        finally:
            node._get_addon_from_gv = original_method

    @patch('osf.models.node.get_current_request')
    @patch('api.waffle.utils.flag_is_active')
    @patch('osf.models.node.OSFUser.load')
    @patch('osf.external.gravy_valet.translations.get_external_services')
    @patch('osf.models.node.AbstractNode._get_addons_from_gv')
    @patch('osf.features.ENABLE_GV', True)
    def test_get_addon_from_gv_with_auth(
        self, mock_get_addons, mock_get_services, mock_load_user, mock_flag, mock_get_request,
        node, user, mock_request, mock_external_service, mock_addon
    ):
        mock_get_request.return_value = mock_request
        mock_flag.return_value = True
        mock_load_user.return_value = user
        mock_get_services.return_value = [mock_external_service]
        mock_get_addons.return_value = [mock_addon]

        auth = Auth(user=user)

        # Make sure request.gv_addons is not set yet
        if hasattr(mock_request, 'gv_addons'):
            delattr(mock_request, 'gv_addons')

        original_method = node._get_addon_from_gv

        def mock_get_addon_from_gv(self, gv_pk, requesting_user_id, auth=None):
            request = mock_get_request()
            # This is to avoid making multiple requests to GV
            # within the lifespan of one request on the OSF side
            try:
                gv_addons = request.gv_addons
            except AttributeError:
                mock_load_user(requesting_user_id)
                services = mock_get_services(user)
                for service in services:
                    if service.short_name == gv_pk:
                        break
                else:
                    return None
                request.gv_addons = mock_get_addons(requesting_user_id, service.type, auth=auth)
                gv_addons = request.gv_addons

            for item in gv_addons:
                if item.short_name == gv_pk:
                    return item
            return None

        from types import MethodType
        node._get_addon_from_gv = MethodType(mock_get_addon_from_gv, node)

        try:
            result = node._get_addon_from_gv('github', user._id, auth=auth)

            assert result == mock_addon
            mock_get_services.assert_called_once_with(user)
            mock_get_addons.assert_called_once_with(user._id, mock_external_service.type, auth=auth)
        finally:
            node._get_addon_from_gv = original_method

    @patch('osf.models.mixins.get_request_and_user_id')
    @patch('api.waffle.utils.flag_is_active')
    @patch('osf.models.node.AbstractNode._get_addon_from_gv')
    @patch('osf.features.ENABLE_GV', True)
    def test_integration_get_addon_calls_get_addon_from_gv(
        self, mock_get_addon_from_gv, mock_flag, mock_get_request_user,
        node, user
    ):
        mock_request = MagicMock()
        mock_get_request_user.return_value = (mock_request, user._id)
        mock_flag.return_value = True
        mock_addon = MagicMock()
        mock_addon.short_name = 'github'
        mock_get_addon_from_gv.return_value = mock_addon

        original_get_addon = node.get_addon

        def mock_get_addon(self, name, is_deleted=False, auth=None):
            if name not in ['osfstorage']:
                request, user_id = mock_get_request_user()
                if mock_flag(request, features.ENABLE_GV):
                    return mock_get_addon_from_gv(gv_pk=name, requesting_user_id=user_id, auth=auth)
            return None

        from types import MethodType
        node.get_addon = MethodType(mock_get_addon, node)

        try:
            result = node.get_addon('github')

            assert result == mock_addon
            mock_get_addon_from_gv.assert_called_once()
            call_args = mock_get_addon_from_gv.call_args[1]
            assert call_args['gv_pk'] == 'github'
            assert call_args['requesting_user_id'] == user._id
            assert call_args['auth'] is None
            mock_flag.assert_called_once()
        finally:
            node.get_addon = original_get_addon

    @patch('osf.models.mixins.get_request_and_user_id')
    @patch('api.waffle.utils.flag_is_active')
    @patch('osf.models.node.AbstractNode._get_addon_from_gv')
    @patch('osf.features.ENABLE_GV', True)
    def test_integration_get_addon_skips_gv_for_osf_hosted_addons(
        self, mock_get_addon_from_gv, mock_flag, mock_get_request_user,
        node, user
    ):
        mock_request = MagicMock()
        mock_get_request_user.return_value = (mock_request, user._id)
        mock_flag.return_value = True

        with patch('osf.models.mixins.AddonModelMixin.OSF_HOSTED_ADDONS',
                   new_callable=PropertyMock) as mock_osf_addons:
            mock_osf_addons.return_value = ['osfstorage', 'wiki']

            node.get_addon('osfstorage', auth=Auth(user=user))

            mock_get_addon_from_gv.assert_not_called()

    @patch('osf.models.mixins.get_request_and_user_id')
    @patch('osf.models.node.AbstractNode._get_addon_from_gv')
    def test_get_addon_uses_auth_user_id_when_request_user_id_is_none(
        self, mock_get_addon_from_gv, mock_get_request_user,
        node, user
    ):
        with override_flag(features.ENABLE_GV, active=True):
            mock_request = MagicMock()
            mock_get_request_user.return_value = (mock_request, None)

            auth = Auth(user=user)

            mock_addon = MagicMock()
            mock_addon.short_name = 'github'
            mock_get_addon_from_gv.return_value = mock_addon

            result = node.get_addon('github', auth=auth)

            mock_get_addon_from_gv.assert_called_once_with(
                gv_pk='github',
                requesting_user_id=user._id,
                auth=auth
            )
            assert result == mock_addon

    @patch('osf.models.mixins.get_request_and_user_id')
    @patch('osf.models.node.AbstractNode._get_addon_from_gv')
    def test_get_addon_uses_request_user_id_when_available(
        self, mock_get_addon_from_gv, mock_get_request_user,
        node, user
    ):
        with override_flag(features.ENABLE_GV, active=True):
            mock_request = MagicMock()
            request_user_id = 'request_user_123'
            mock_get_request_user.return_value = (mock_request, request_user_id)

            auth = Auth(user=user)

            mock_addon = MagicMock()
            mock_addon.short_name = 'github'
            mock_get_addon_from_gv.return_value = mock_addon

            result = node.get_addon('github', auth=auth)

            mock_get_addon_from_gv.assert_called_once_with(
                gv_pk='github',
                requesting_user_id=request_user_id,
                auth=auth
            )
            assert result == mock_addon

    @patch('osf.models.mixins.get_request_and_user_id')
    @patch('osf.models.node.AbstractNode._get_addon_from_gv')
    def test_get_addon_handles_none_auth_gracefully(
        self, mock_get_addon_from_gv, mock_get_request_user,
        node, user
    ):
        with override_flag(features.ENABLE_GV, active=True):
            mock_request = MagicMock()
            mock_get_request_user.return_value = (mock_request, None)

            mock_addon = MagicMock()
            mock_addon.short_name = 'github'
            mock_get_addon_from_gv.return_value = mock_addon

            result = node.get_addon('github', auth=None)

            mock_get_addon_from_gv.assert_called_once_with(
                gv_pk='github',
                requesting_user_id=None,
                auth=None
            )
            assert result == mock_addon

    @patch('osf.models.mixins.get_request_and_user_id')
    def test_get_addon_skips_gv_for_osf_hosted_addons_with_auth(
        self, mock_get_request_user, node, user
    ):
        with override_flag(features.ENABLE_GV, active=True):
            mock_request = MagicMock()
            mock_get_request_user.return_value = (mock_request, None)

            auth = Auth(user=user)

            node.get_addon('osfstorage', auth=auth)

            mock_get_request_user.assert_not_called()

    @patch('osf.models.mixins.get_request_and_user_id')
    @patch('osf.models.node.AbstractNode._get_addon_from_gv')
    def test_get_addon_with_auth_user_none_falls_back_to_request_user_id(
        self, mock_get_addon_from_gv, mock_get_request_user,
        node, user
    ):
        with override_flag(features.ENABLE_GV, active=True):
            mock_request = MagicMock()
            request_user_id = 'request_user_123'
            mock_get_request_user.return_value = (mock_request, request_user_id)

            auth = Auth(user=None)

            mock_addon = MagicMock()
            mock_addon.short_name = 'github'
            mock_get_addon_from_gv.return_value = mock_addon

            result = node.get_addon('github', auth=auth)

            mock_get_addon_from_gv.assert_called_once_with(
                gv_pk='github',
                requesting_user_id=request_user_id,
                auth=auth
            )
            assert result == mock_addon


@pytest.mark.django_db
class TestGVTranslationsOptimization:

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def mock_service_result(self):
        mock_result = MagicMock()
        mock_result.get_attribute.return_value = 'github'
        mock_result.resource_type = 'external-storage-services'
        return mock_result

    @patch('osf.external.gravy_valet.translations._services', None)
    @patch('osf.external.gravy_valet.request_helpers.iterate_gv_results')
    def test_get_external_services_caches_results(self, mock_iterate_results, user, mock_service_result):
        mock_iterate_results.return_value = [mock_service_result]

        with patch.object(gv_requests, 'AddonType') as mock_addon_type:
            storage_type = MagicMock()
            storage_type.__str__ = MagicMock(return_value='storage')

            mock_addon_type.STORAGE = storage_type
            mock_addon_type.__iter__.return_value = [storage_type]

            services1 = gv_translations.get_external_services(user)

            assert len(services1) == 1
            assert services1[0].short_name == 'github'
            mock_iterate_results.assert_called()

            mock_iterate_results.reset_mock()

            services2 = gv_translations.get_external_services(user)

            assert len(services2) == 1
            assert services2[0].short_name == 'github'
            mock_iterate_results.assert_not_called()

            assert services1 == services2

    @patch('osf.external.gravy_valet.translations._services', None)
    @patch('osf.external.gravy_valet.request_helpers.iterate_gv_results')
    def test_get_external_services_multiple_addon_types(self, mock_iterate_results, user):
        mock_storage = MagicMock()
        mock_storage.get_attribute.return_value = 'github'
        mock_storage.resource_type = 'external-storage-services'

        mock_citation = MagicMock()
        mock_citation.get_attribute.return_value = 'zotero'
        mock_citation.resource_type = 'external-citation-services'

        def side_effect(endpoint_url, requesting_user, **kwargs):
            if 'storage' in endpoint_url:
                return [mock_storage]
            elif 'citation' in endpoint_url:
                return [mock_citation]
            return []

        mock_iterate_results.side_effect = side_effect

        with patch.object(gv_requests, 'AddonType') as mock_addon_type:
            storage_type = MagicMock()
            storage_type.__str__ = MagicMock(return_value='storage')
            citation_type = MagicMock()
            citation_type.__str__ = MagicMock(return_value='citation')

            mock_addon_type.STORAGE = storage_type
            mock_addon_type.CITATION = citation_type
            mock_addon_type.__iter__.return_value = [storage_type, citation_type]

            services = gv_translations.get_external_services(user)

            assert len(services) == 2
            assert any(s.short_name == 'github' for s in services)
            assert any(s.short_name == 'zotero' for s in services)

            assert mock_iterate_results.call_count == 2
