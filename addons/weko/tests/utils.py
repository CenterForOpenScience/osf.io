# -*- coding: utf-8 -*-
from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.weko.models import WEKOProvider
from addons.weko.serializer import WEKOSerializer
from addons.weko.tests.factories import WEKOAccountFactory


fake_weko_host = 'https://test.sample.nii.ac.jp/sword/'
fake_weko_indices = [
    {
        'id': 100,
        'name': 'Sample Index',
        'children': [
            {
                'id': 'more',
            },
            {
                'id': 'dummy',
            }
        ],
    },
    {
        'id': 'more',
    },
]
fake_weko_item = {
    'id': 1000,
    'metadata': {
        'title': 'Sample Item',
    },
}
fake_weko_items = {
    'hits': {
        'hits': [
            fake_weko_item,
            {
                'id': 'dummy',
            }
        ]
    },
}

class MockResponse:
    def __init__(self, json, status_code):
        self._json = json
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code in [200]:
            return
        raise IOError(f'status code: {self.status_code}')


mock_response_404 = MockResponse('404 not found', 404)


class WEKOAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'weko'
    ExternalAccountFactory = WEKOAccountFactory
    Provider = WEKOProvider
    Serializer = WEKOSerializer
    client = None
    folder = {
    	'path': 'container',
    	'name': 'container',
    	'id': 'container'
	}
