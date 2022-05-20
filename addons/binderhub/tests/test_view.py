# -*- coding: utf-8 -*-
from rest_framework import status as http_status

import mock
from nose.tools import *  # noqa

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory

from .. import SHORT_NAME
from ..models import BinderHubToken
from .. import settings
from .factories import make_binderhub, make_tljh
from .utils import BaseAddonTestCase
from website.util import api_url_for
from future.moves.urllib.parse import urlparse, parse_qs


class TestViews(BaseAddonTestCase, OsfTestCase):

    def test_user_binderhubs(self):
        new_binderhub_a = make_binderhub(
            binderhub_url='https://testa.my.site',
            binderhub_oauth_client_secret='MY_CUSTOM_SECRET_A',
        )
        url = self.project.api_url_for('{}_set_user_config'.format(SHORT_NAME))
        res = self.app.put_json(url, {
            'binderhubs': [new_binderhub_a],
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_get_user_config'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        binderhubs = res.json['binderhubs']
        assert_equals(len(binderhubs), 1)
        assert_equals(binderhubs[0]['binderhub_url'], 'https://testa.my.site')
        assert_in('binderhub_oauth_client_secret', binderhubs[0])

        new_binderhub_b = make_binderhub(
            binderhub_url='https://testb.my.site',
            binderhub_oauth_client_secret='MY_CUSTOM_SECRET_B',
        )
        url = self.project.api_url_for('{}_add_user_config'.format(SHORT_NAME))
        res = self.app.post_json(url, {
            'binderhub': new_binderhub_b,
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_get_user_config'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        binderhubs = res.json['binderhubs']
        assert_equals(len(binderhubs), 2)
        assert_equals(binderhubs[0]['binderhub_url'], 'https://testa.my.site')
        assert_in('binderhub_oauth_client_secret', binderhubs[0])
        assert_equals(binderhubs[1]['binderhub_url'], 'https://testb.my.site')
        assert_in('binderhub_oauth_client_secret', binderhubs[1])

        new_binderhub_c = make_tljh(
            tljh_url='https://testc.my.site',
        )
        url = self.project.api_url_for('{}_add_user_config'.format(SHORT_NAME))
        res = self.app.post_json(url, {
            'binderhub': new_binderhub_c,
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_get_user_config'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        binderhubs = res.json['binderhubs']
        assert_equals(len(binderhubs), 3)
        assert_equals(binderhubs[0]['binderhub_url'], 'https://testa.my.site')
        assert_in('binderhub_oauth_client_secret', binderhubs[0])
        assert_equals(binderhubs[1]['binderhub_url'], 'https://testb.my.site')
        assert_in('binderhub_oauth_client_secret', binderhubs[1])
        assert_equals(binderhubs[2]['binderhub_url'], 'https://testc.my.site')
        assert_in('binderhub_oauth_client_secret', binderhubs[2])

    def test_binderhub_authorize(self):
        url = self.project.api_url_for('{}_oauth_authorize'.format(SHORT_NAME),
                                       serviceid='binderhub')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http_status.HTTP_302_FOUND)
        url = res.headers['Location']
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert_equal(params['response_type'][0], 'code')
        assert_equal(params['scope'][0], 'identity')
        assert_equal(urlparse(params['redirect_uri'][0]).path, '/project/binderhub/callback')

    def test_empty_binder_url(self):
        self.node_settings.set_binder_url('')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['binder_url'], settings.DEFAULT_BINDER_URL)

    def test_binder_url(self):
        self.node_settings.set_binder_url('URL_1')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['binder_url'], 'URL_1')

    def test_ember_empty_binder_url(self):
        url = self.project.api_url_for('{}_set_config'.format(SHORT_NAME))
        res = self.app.put_json(url, {
            'binder_url': '',
            'available_binderhubs': [],
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['data']['id'], self.project._id)
        assert_equals(res.json['data']['type'], 'binderhub-config')
        binderhubs = res.json['data']['attributes']['binderhubs']
        default_binderhub = [b for b in binderhubs if b['default']][0]
        assert_equals(default_binderhub['url'], settings.DEFAULT_BINDER_URL)
        assert_not_in('binderhub_oauth_client_secret', default_binderhub)

    def test_ember_custom_binder_url(self):
        new_binderhub = make_binderhub(
            binderhub_url='https://testa.my.site',
            binderhub_oauth_client_secret='MY_CUSTOM_SECRET_A',
            binderhub_oauth_authorize_url='https://testa.my.site/authorize',
            jupyterhub_url='https://testa.jh.my.site',
        )
        url = self.project.api_url_for('{}_set_config'.format(SHORT_NAME))
        res = self.app.put_json(url, {
            'binder_url': 'https://testa.my.site',
            'available_binderhubs': [new_binderhub],
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['data']['id'], self.project._id)
        assert_equals(res.json['data']['type'], 'binderhub-config')
        binderhubs = res.json['data']['attributes']['binderhubs']
        default_binderhub = [b for b in binderhubs if b['default']][0]
        assert_equals(default_binderhub['url'], 'https://testa.my.site')
        assert_in(
            '/binderhub/binderhub/authorize?binderhub_url=https%3A%2F%2Ftesta.my.site',
            default_binderhub['authorize_url'],
        )
        assert_not_in('binderhub_oauth_client_secret', default_binderhub)
        jupyterhubs = res.json['data']['attributes']['jupyterhubs']
        assert_equals(len(jupyterhubs), 0)

        token = BinderHubToken.objects.create(
            user=self.user,
            node=self.project,
            binderhub_url='https://testa.my.site',
            jupyterhub_url='https://testa.jh.my.site',
        )
        token.save()
        url = self.project.api_url_for('{}_set_config'.format(SHORT_NAME))
        res = self.app.put_json(url, {
            'binder_url': 'https://testa.my.site',
            'available_binderhubs': [new_binderhub],
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['data']['id'], self.project._id)
        assert_equals(res.json['data']['type'], 'binderhub-config')
        binderhubs = res.json['data']['attributes']['binderhubs']
        default_binderhub = [b for b in binderhubs if b['default']][0]
        assert_equals(default_binderhub['url'], 'https://testa.my.site')
        assert_in(
            '/binderhub/binderhub/authorize?binderhub_url=https%3A%2F%2Ftesta.my.site',
            default_binderhub['authorize_url'],
        )
        assert_not_in('binderhub_oauth_client_secret', default_binderhub)
        jupyterhubs = res.json['data']['attributes']['jupyterhubs']
        assert_equals(len(jupyterhubs), 1)
        default_jupyterhub = [jh for jh in jupyterhubs
                              if jh['url'] == default_binderhub['jupyterhub_url']][0]
        assert_equals(default_jupyterhub['max_servers'], None)
        assert_in(
            '/binderhub/session?binderhub_url=https%3A%2F%2Ftesta.my.site',
            default_jupyterhub['logout_url'],
        )

        new_binderhub = make_binderhub(
            binderhub_url='https://testa.my.site',
            binderhub_oauth_client_secret='MY_CUSTOM_SECRET_A',
            binderhub_oauth_authorize_url='https://testa.my.site/authorize',
            jupyterhub_max_servers=10,
        )
        url = self.project.api_url_for('{}_set_config'.format(SHORT_NAME))
        res = self.app.put_json(url, {
            'binder_url': 'https://testa.my.site',
            'available_binderhubs': [new_binderhub],
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        binderhubs = res.json['data']['attributes']['binderhubs']
        default_binderhub = [b for b in binderhubs if b['default']][0]
        jupyterhubs = res.json['data']['attributes']['jupyterhubs']
        default_jupyterhub = [jh for jh in jupyterhubs
                              if jh['url'] == default_binderhub['jupyterhub_url']][0]
        assert_equals(default_jupyterhub['max_servers'], 10)

        new_binderhub = make_binderhub(
            binderhub_url='https://testa.my.site',
            binderhub_oauth_client_secret='MY_CUSTOM_SECRET_A',
            binderhub_oauth_authorize_url='https://testa.my.site/authorize',
            jupyterhub_max_servers=10,
        )
        del new_binderhub['jupyterhub_max_servers']
        url = self.project.api_url_for('{}_set_config'.format(SHORT_NAME))
        res = self.app.put_json(url, {
            'binder_url': 'https://testa.my.site',
            'available_binderhubs': [new_binderhub],
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        binderhubs = res.json['data']['attributes']['binderhubs']
        default_binderhub = [b for b in binderhubs if b['default']][0]
        jupyterhubs = res.json['data']['attributes']['jupyterhubs']
        default_jupyterhub = [jh for jh in jupyterhubs
                              if jh['url'] == default_binderhub['jupyterhub_url']][0]
        assert_equals(default_jupyterhub['max_servers'], None)

    def test_ember_custom_tljh_url(self):
        new_binderhub = make_tljh(
            tljh_url='https://testa.my.site',
        )
        url = self.project.api_url_for('{}_set_config'.format(SHORT_NAME))
        res = self.app.put_json(url, {
            'binder_url': 'https://testa.my.site',
            'available_binderhubs': [new_binderhub],
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['data']['id'], self.project._id)
        assert_equals(res.json['data']['type'], 'binderhub-config')
        binderhubs = res.json['data']['attributes']['binderhubs']
        default_binderhub = [b for b in binderhubs if b['default']][0]
        assert_equals(default_binderhub['url'], 'https://testa.my.site')
        assert_equals(default_binderhub['authorize_url'], None)
        assert_not_in('binderhub_oauth_client_secret', default_binderhub)

    def test_logout(self):
        new_binderhub = make_binderhub(
            binderhub_url='https://testa.my.site',
            binderhub_oauth_client_secret='MY_CUSTOM_SECRET_A',
            binderhub_oauth_authorize_url='https://testa.my.site/authorize',
            jupyterhub_url='https://testa.jh.my.site',
        )
        url = self.project.api_url_for('{}_set_config'.format(SHORT_NAME))
        res = self.app.put_json(url, {
            'binder_url': 'https://testa.my.site',
            'available_binderhubs': [new_binderhub],
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_logout'.format(SHORT_NAME))
        res = self.app.delete(url + '?binderhub_url=https%3A%2F%2Ftesta.my.site', auth=self.user.auth)
        assert_equals(res.json['data']['deleted'], 0)
        assert_equals(res.json['data']['jupyterhub_logout_url'], 'https://testa.jh.my.site/hub/logout')

        token = BinderHubToken.objects.create(
            user=self.user,
            node=self.project,
            binderhub_url='https://testa.my.site',
            jupyterhub_url='https://testa.jh.my.site',
        )
        token.save()
        url = self.project.api_url_for('{}_logout'.format(SHORT_NAME))
        res = self.app.delete(url + '?binderhub_url=https%3A%2F%2Ftesta.my.site', auth=self.user.auth)
        assert_equals(res.json['data']['deleted'], 1)
        assert_equals(res.json['data']['jupyterhub_logout_url'], 'https://testa.jh.my.site/hub/logout')

        new_binderhub = make_binderhub(
            binderhub_url='https://testa.my.site',
            binderhub_oauth_client_secret='MY_CUSTOM_SECRET_A',
            binderhub_oauth_authorize_url='https://testa.my.site/authorize',
            jupyterhub_url='https://testa.jh.my.site',
            jupyterhub_logout_url='https://testa.jh.my.site/custom/logout',
        )
        url = self.project.api_url_for('{}_set_config'.format(SHORT_NAME))
        res = self.app.put_json(url, {
            'binder_url': 'https://testa.my.site',
            'available_binderhubs': [new_binderhub],
        }, auth=self.user.auth)
        url = self.project.api_url_for('{}_logout'.format(SHORT_NAME))
        res = self.app.delete(url + '?binderhub_url=https%3A%2F%2Ftesta.my.site', auth=self.user.auth)
        assert_equals(res.json['data']['deleted'], 1)
        assert_equals(res.json['data']['jupyterhub_logout_url'], 'https://testa.jh.my.site/custom/logout')
