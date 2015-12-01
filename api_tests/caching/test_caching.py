from __future__ import unicode_literals
import copy

import requests
from datadiff import diff
from django.conf import settings
from requests.auth import HTTPBasicAuth


class TestVarnish(object):

    local_varnish_base_url = 'http://localhost:8193/v2/'
    local_python_base_url = 'http://localhost:8000/v2/'

    def setUp(self):
        if not settings.RUN_VARNISH_IN_DEV:
            return
        self.authorization = HTTPBasicAuth('mocha@osf.io', 'password')

    def test_compare_python_responses_to_varnish_responses(self):
        if not settings.RUN_VARNISH_IN_DEV:
            return
        querystrings = dict(
            nodes=[
                'comments',
                'children',
                'files',
                'registrations',
                'contributors',
                'node_links',
                'parent',
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
                'parent',
                'registrations',
                'registered_by',
                'registered_from',
            ]
        )

        querystring_suffix = 'page[size]=10&format=jsonapi'

        data_dict = dict(
            nodes=dict(),
            users=dict(),
            comments=dict(),
            registrations=dict(),
        )

        python_data = copy.deepcopy(data_dict)
        python_authed_data = copy.deepcopy(data_dict)
        varnish_data = copy.deepcopy(data_dict)
        varnish_authed_data = copy.deepcopy(data_dict)

        for key, embed_values in querystrings.items():
            embed_values.sort()
            original_embed_values = embed_values
            while len(embed_values) > 0:
                generated_qs = '&embed='.join(embed_values)
                python_url = '{}{}/?embed={}&{}'.format(self.local_python_base_url, key, generated_qs, querystring_suffix)
                varnish_url = '{}{}/?embed={}&{}&esi=true'.format(self.local_varnish_base_url, key, generated_qs,
                                                                                         querystring_suffix)

                python_resp = requests.get(python_url, timeout=120)

                varnish_resp = requests.get(varnish_url, timeout=120)

                python_authed_resp = requests.get(python_url, auth=self.authorization, timeout=120)

                varnish_authed_resp = requests.get(varnish_url, auth=self.authorization, timeout=120)


                try:
                    python_data[key]['_'.join(embed_values)] = python_resp.json()
                    self.validate_keys(python_resp.json(), original_embed_values)
                except AssertionError as ex:
                    print 'Validation failed python_url unauthed: {} - {}\n\n\n'.format(python_url, ex.message)
                except Exception as ex:
                    python_data[key]['_'.join(embed_values)] = dict(error=ex.message)
                    print 'Failed to get python_url unauthed: {} - {}\n\n\n'.format(python_url, ex.message)

                try:
                    python_authed_data[key]['_'.join(embed_values)] = python_authed_resp.json()
                    self.validate_keys(python_authed_resp.json(), original_embed_values)
                except AssertionError as ex:
                    print 'Validation failed python_url authed: {} - {}\n\n\n'.format(python_url, ex.message)
                except Exception as ex:
                    python_authed_data[key]['_'.join(embed_values)] = dict(error=ex.message)
                    print 'Failed to get python_url authed: {} - {}\n\n\n'.format(python_url, ex.message)

                try:
                    varnish_data[key]['_'.join(embed_values)] = varnish_resp.json()
                    self.validate_keys(varnish_resp.json(), original_embed_values)
                except AssertionError as ex:
                    print 'Validation failed varnish_url unauthed: {} - {}\n\n\n'.format(varnish_url, ex.message)
                except Exception as ex:
                    varnish_data[key]['_'.join(embed_values)] = dict(error=ex.message)
                    print 'Failed to get and validate varnish_url unauthed: {} - {}\n\n\n'.format(varnish_url,
                                                                                                  ex.message)

                try:
                    varnish_authed_data[key]['_'.join(embed_values)] = varnish_authed_resp.json()
                    self.validate_keys(varnish_authed_resp.json(), original_embed_values)
                except AssertionError as ex:
                    print 'Validation failed varnish_url authed: {} - {}\n\n\n'.format(varnish_url, ex.message)
                except Exception as ex:
                    varnish_authed_data[key]['_'.join(embed_values)] = dict(error=ex.message)
                    print 'Failed to get and validate varnish_url authed: {} - {}\n\n\n'.format(varnish_url, ex.message)

                embed_values.pop()

        # Uncomment these lines to write out files containing responses for comparison

        # for item_type, item in python_data.items():
        #     for embed_type, data in item.items():
        #         with open('./python_data_{}_{}.json'.format(item_type, embed_type),
        #                   'w') as fp:
        #             fp.write(json.dumps(python_data[item_type][embed_type], indent=4))
        #             fp.close()
        #
        # for item_type, item in varnish_data.items():
        #     for embed_type, data in item.items():
        #         with open('./varnish_data_{}_{}.json'.format(item_type, embed_type),
        #                   'w') as fp:
        #             fp.write(json.dumps(varnish_data[item_type][embed_type], indent=4))
        #             fp.close()
        #
        # for item_type, item in varnish_data.items():
        #     for embed_type, data in item.items():
        #         delta = diff(python_data[item_type][embed_type], varnish_data[item_type][embed_type])
        #         with open('./data_diff_{}_{}.diff'.format(item_type, embed_type),
        #                   'w') as fp:
        #             fp.write(str(delta))
        #             fp.close()
        #
        # for item_type, item in python_authed_data.items():
        #     for embed_type, data in item.items():
        #         with open('./python_authed_data_{}_{}.json'.format(item_type, embed_type),
        #                   'w') as fp:
        #             fp.write(json.dumps(python_data[item_type][embed_type], indent=4))
        #             fp.close()
        #
        # for item_type, item in varnish_authed_data.items():
        #     for embed_type, data in item.items():
        #         with open('./varnish_authed_data_{}_{}.json'.format(item_type, embed_type),
        #                   'w') as fp:
        #             fp.write(json.dumps(varnish_data[item_type][embed_type], indent=4))
        #             fp.close()
        #
        # for item_type, item in varnish_authed_data.items():
        #     for embed_type, data in item.items():
        #         delta = diff(python_authed_data[item_type][embed_type], varnish_authed_data[item_type][embed_type])
        #         with open('./data_diff_authed_{}_{}.diff'.format(item_type, embed_type),
        #                   'w') as fp:
        #             fp.write(str(delta))
        #             fp.close()

    def validate_keys(self, data, embed_keys=list()):
        """
        validate_keys confirms that the correct keys are in embeds and relationships.
        """
        for item in data['data']:  # all these should be lists.

            if 'embeds' in item.keys():
                item__embed_keys = item['embeds'].keys()
                item__embed_keys.sort()
                embed_keys.sort()
                assert item__embed_keys == embed_keys, 'Embed key mismatch: {}'.format(
                    diff(item__embed_keys, embed_keys))
            if 'relationships' in item.keys():
                for rel_key in item['relationships'].keys():
                    assert unicode(rel_key) not in embed_keys, 'Relationship mismatch: {}'.format(rel_key)

    def test_cache_invalidation(self):
        if not settings.RUN_VARNISH_IN_DEV:
            return
        payload = dict(
            data=dict(
                type='nodes',
                attributes=dict(
                    title='Awesome Test Node Title',
                    category='project'
                )
            )
        )

        create_response = requests.post('{}nodes/'.format(self.local_python_base_url), json=payload, auth=self.authorization)
        assert create_response.ok, 'Failed to create node'

        node_id = create_response.json()['data']['id']
        new_title = "{} -- But Changed!".format(create_response.json()['data']['attributes']['title'])

        response = requests.get(
            'http://localhost:8193/v2/nodes/{}/?format=jsonapi&embed=comments&embed=children&embed=files&embed=registrations&embed=contributors&embed=node_links&embed=parent'.format(
                node_id),
            timeout=120,
            auth=self.authorization
        )
        assert response.ok, 'Your request failed.'

        new_data_object = dict(data=dict())
        new_data_object['data']['id'] = node_id
        new_data_object['data']['type'] = 'nodes'
        new_data_object['data']['attributes'] = dict(title=new_title, category='')

        individual_response_before_update = requests.get('http://localhost:8193/v2/nodes/{}/'.format(node_id),
                                                         auth=self.authorization)

        assert individual_response_before_update.ok, 'Individual request failed.'

        individual_response_before_update = requests.get('http://localhost:8193/v2/nodes/{}/'.format(node_id),
                                                         auth=self.authorization)

        assert individual_response_before_update.ok, 'Individual request failed.'

        assert individual_response_before_update.headers['x-cache'] == 'HIT', 'Request never made it to cache'

        update_response = requests.put('http://localhost:8193/v2/nodes/{}/'.format(node_id), json=new_data_object,
                                       auth=self.authorization)


        assert update_response.ok, 'Your update request failed. {}'.format(update_response.text)

        individual_response = requests.get('http://localhost:8193/v2/nodes/{}/'.format(node_id), auth=self.authorization)


        assert individual_response.ok, 'Your individual node request failed. {}'.format(individual_response.json())

        assert individual_response.headers['x-cache'] == 'MISS', 'Request got a cache hit.'
