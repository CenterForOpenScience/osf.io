from __future__ import unicode_literals

import copy
import json
import random
import unittest
import uuid

import requests
from django.conf import settings as django_settings
from requests.auth import HTTPBasicAuth

from framework.auth import User
from tests.factories import create_fake_project
from tests.base import DbTestCase


# import datadiff
# from datadiff import tools

class TestVarnish(DbTestCase):
    local_varnish_base_url = '{}/v2/'.format(django_settings.VARNISH_SERVERS[0])
    local_python_base_url = 'http://localhost:8000/v2/'

    @classmethod
    def setUpClass(cls):
        super(TestVarnish, cls).setUpClass()
        username = uuid.uuid4()
        cls.user = User.create_confirmed(
            username='{}@example.com'.format(str(username)),
            password='password',
            fullname='Mocha Test User')
        cls.user.save()
        cls.authorization = HTTPBasicAuth(cls.user.username, 'password')

        small = 5
        large = 10

        components = [[[range(small, random.randint(small, large))
                        for x in range(small, random.randint(small, large))]
                       for y in range(small, random.randint(small, large))]
                      for z in range(small, random.randint(small, large))]

        number_of_projects = random.randint(1, 11)
        number_of_tags = random.randint(1, 11)
        number_of_users = random.randint(1, 11)

        for i in range(number_of_projects):
            name = ''
            create_fake_project(cls.user, number_of_users,
                                random.choice(['public', 'private']),
                                components, name, number_of_tags, None, False)

    @unittest.skipIf(not django_settings.ENABLE_VARNISH, 'Varnish is disabled')
    def test_compare_python_responses_to_varnish_responses(self):
        querystrings = dict(
            nodes=[
                'comments',
                'children',
                'files',
                'registrations',
                'contributors',
                'node_links',
                'root',
            ],
            users=[
                'nodes',
            ],
            registrations=[
                'comments',
                'children',
                'files',
                'registrations',
                'contributors',
                'node_links',
                'root',
                'registrations',
                'registered_by',
                'registered_from',
            ]
        )

        querystring_suffix = 'page[size]=10&format=jsonapi&sort=_id'

        data_dict = dict(nodes=dict(),
                         users=dict(),
                         comments=dict(),
                         registrations=dict(), )

        python_data = copy.deepcopy(data_dict)
        python_authed_data = copy.deepcopy(data_dict)
        varnish_data = copy.deepcopy(data_dict)
        varnish_authed_data = copy.deepcopy(data_dict)

        for key, embed_values in querystrings.items():
            embed_values.sort()
            original_embed_values = embed_values
            while len(embed_values) > 0:
                generated_qs = '&embed='.join(embed_values)
                python_url = '{}{}/?embed={}&{}&esi=false'.format(
                    self.local_python_base_url, key, generated_qs,
                    querystring_suffix)
                varnish_url = '{}{}/?embed={}&{}&esi=true'.format(
                    self.local_varnish_base_url, key, generated_qs,
                    querystring_suffix)
                python_resp = requests.get(python_url, timeout=120)
                python_authed_resp = requests.get(python_url,
                                                  auth=self.authorization,
                                                  timeout=120)

                varnish_resp = requests.get(varnish_url, timeout=120)
                varnish_authed_resp = requests.get(varnish_url,
                                                   auth=self.authorization,
                                                   timeout=120)

                python_data[key]['_'.join(
                    embed_values)] = python_resp.json()
                self.validate_keys(python_resp.json(),
                                   original_embed_values)

                python_authed_data[key]['_'.join(
                    embed_values)] = python_authed_resp.json()
                self.validate_keys(python_authed_resp.json(),
                                   original_embed_values)

                varnish_data[key]['_'.join(
                    embed_values)] = varnish_resp.json()
                self.validate_keys(varnish_resp.json(),
                                   original_embed_values)

                varnish_authed_data[key]['_'.join(
                    embed_values)] = varnish_authed_resp.json()
                self.validate_keys(varnish_authed_resp.json(),
                                   original_embed_values)

                # varnish_json = json.loads(varnish_resp.text.replace('localhost:8193', 'localhost:8000'))
                # varnish_authed_json = json.loads(varnish_authed_resp.text.replace('localhost:8193', 'localhost:8000'))
                #
                # tools.assert_equal(varnish_json, python_resp.json())
                # tools.assert_equal(varnish_authed_json, python_authed_resp.json())

                embed_values.pop()

    def validate_keys(self, data, embed_keys):
        """
        validate_keys confirms that the correct keys are in embeds and relationships.
        """
        if embed_keys is None:
            embed_keys = list()

        if 'errors' in data.keys():
            print json.dumps(data, indent=4)
            return
        for item in data['data']:  # all these should be lists.
            if 'embeds' in item.keys():
                item__embed_keys = item['embeds'].keys()
                item__embed_keys.sort()
                embed_keys.sort()
                assert item__embed_keys == embed_keys, 'Embed key mismatch: \n{}\n{}'.format(item__embed_keys,
                                                                                             embed_keys)
            if 'relationships' in item.keys():
                for rel_key in item['relationships'].keys():
                    assert unicode(
                        rel_key) not in embed_keys, 'Relationship mismatch: {}'.format(
                        rel_key)

    @unittest.skipIf(not django_settings.ENABLE_VARNISH, 'Varnish is disabled')
    def test_cache_invalidation(self):
        payload = dict(
            data=dict(type='nodes',
                      attributes=dict(title='Awesome Test Node Title',
                                      category='project')))
        create_response = requests.post(
            '{}nodes/'.format(self.local_python_base_url),
            json=payload,
            auth=self.authorization)
        assert create_response.ok, 'Failed to create node'

        node_id = create_response.json()['data']['id']
        new_title = '{} -- But Changed!'.format(create_response.json()['data']['attributes']['title'])

        response = requests.get(
            '{}/v2/nodes/{}/?format=jsonapi&esi=true&embed=comments&embed=children&embed=files&embed=registrations&embed=contributors&embed=node_links&embed=parent'.format(
                django_settings.VARNISH_SERVERS[0], node_id),
            timeout=120,
            auth=self.authorization)
        assert response.ok, 'Your request failed.'

        new_data_object = dict(data=dict())
        new_data_object['data']['id'] = node_id
        new_data_object['data']['type'] = 'nodes'
        new_data_object['data']['attributes'] = dict(title=new_title,
                                                     category='')

        individual_response_before_update = requests.get(
            '{}/v2/nodes/{}/'.format(django_settings.VARNISH_SERVERS[0],
                                     node_id),
            auth=self.authorization)

        assert individual_response_before_update.ok, 'Individual request failed.'

        individual_response_before_update = requests.get(
            '{}/v2/nodes/{}/'.format(django_settings.VARNISH_SERVERS[0],
                                     node_id),
            auth=self.authorization)

        assert individual_response_before_update.ok, 'Individual request failed.'

        assert individual_response_before_update.headers['x-cache'] == 'HIT', 'Request never made it to cache'

        update_response = requests.put('{}/v2/nodes/{}/'.format(django_settings.VARNISH_SERVERS[0], node_id),
                                       json=new_data_object, auth=self.authorization)

        assert update_response.ok, 'Your update request failed. {}'.format(
            update_response.text)

        individual_response = requests.get('{}/v2/nodes/{}/'.format(
            django_settings.VARNISH_SERVERS[0], node_id),
            auth=self.authorization
        )

        assert individual_response.ok, 'Your individual node request failed. {}'.format(
            individual_response.json())

        assert individual_response.headers['x-cache'] == 'MISS', 'Request got a cache hit.'
