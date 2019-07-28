
import mock
from flask import request

from tests.base import OsfTestCase
from website.ember_osf_web.decorators import ember_flag_is_active
from osf_tests.factories import FlagFactory, UserFactory

from django.contrib.auth.models import Group


class TestEmberFlagIsActive(OsfTestCase):

    def setUp(self):
        super(TestEmberFlagIsActive, self).setUp()
        self.flag = FlagFactory(name='active_flag')
        FlagFactory(name='inactive_flag', everyone=False).save()
        self.mock_func = lambda: 'test value'

    @mock.patch('website.ember_osf_web.decorators.use_ember_app')
    def test_use_ember_app(self, mock_use_ember_app):
        ember_flag_is_active('active_flag')(self.mock_func)()

        mock_use_ember_app.assert_called_with()

    @mock.patch('website.ember_osf_web.decorators.use_ember_app')
    def test_dont_use_ember_app(self, mock_use_ember_app):
        # mock over external module 'waflle.flag_is_active` not ours

        ember_flag_is_active('inactive_flag')(self.mock_func)()

        assert not mock_use_ember_app.called

    @mock.patch('api.waffle.utils._get_current_user')
    @mock.patch('website.ember_osf_web.decorators.waffle.flag_is_active')
    @mock.patch('website.ember_osf_web.decorators.use_ember_app')
    def test_ember_flag_is_active_authenticated_user(self, mock_use_ember_app, mock_flag_is_active, mock__get_current_user):
        # mock over external module 'waflle.flag_is_active` not ours

        user = UserFactory()
        mock__get_current_user.return_value = user

        ember_flag_is_active('active_flag')(self.mock_func)()

        mock_flag_is_active.assert_called_with(request, 'active_flag')
        mock_use_ember_app.assert_called_with()

    @mock.patch('api.waffle.utils._get_current_user', return_value=None)
    @mock.patch('website.ember_osf_web.decorators.waffle.flag_is_active')
    @mock.patch('website.ember_osf_web.decorators.use_ember_app')
    def test_ember_flag_is_active_unauthenticated_user(self, mock_use_ember_app, mock_flag_is_active, mock__get_current_user):
        # mock over external module 'waflle.flag_is_active` not ours

        ember_flag_is_active('active_flag')(self.mock_func)()
        group = Group.objects.create(name='foo')

        self.flag.groups.add(group)

        mock_flag_is_active.assert_called_with(request, 'active_flag')
        mock_use_ember_app.assert_called_with()
