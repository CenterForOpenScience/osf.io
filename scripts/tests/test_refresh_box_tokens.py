# -*- coding: utf-8 -*-

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase

from website.addons.box.tests import factories

import datetime

from dateutil.relativedelta import relativedelta

from website.addons.box import model

from scripts.refresh_box_tokens import get_targets, main


class TestRefreshTokens(OsfTestCase):

    def tearDown(self):
        super(TestRefreshTokens, self).tearDown()
        model.BoxOAuthSettings.remove()

    def test_get_targets(self):
        now = datetime.datetime.utcnow()
        records = [
            factories.BoxOAuthSettingsFactory(expires_at=now + datetime.timedelta(days=8)),
            factories.BoxOAuthSettingsFactory(expires_at=now + datetime.timedelta(days=6)),
        ]
        targets = list(get_targets(delta=relativedelta(days=7)))
        assert_in(records[1], targets)
        assert_not_in(records[0], targets)

    @mock.patch('website.addons.box.model.BoxOAuthSettings.refresh_access_token')
    def test_refresh(self, mock_refresh):
        factories.BoxOAuthSettingsFactory(expires_at=datetime.datetime.utcnow())
        main(delta=relativedelta(days=7), dry_run=False)
        mock_refresh.assert_called_once_with(force=True)
