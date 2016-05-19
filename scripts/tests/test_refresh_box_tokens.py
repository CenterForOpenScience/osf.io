# -*- coding: utf-8 -*-

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase

from website.addons.box.tests import factories

import datetime

from dateutil.relativedelta import relativedelta

from website.oauth.models import ExternalAccount

from scripts.refresh_box_tokens import get_targets, main


class TestRefreshTokens(OsfTestCase):

    def tearDown(self):
        super(TestRefreshTokens, self).tearDown()
        ExternalAccount.remove()

    def test_get_targets(self):
        now = datetime.datetime.utcnow()
        records = [
            factories.BoxAccountFactory(expires_at=now + datetime.timedelta(days=8)),
            factories.BoxAccountFactory(expires_at=now + datetime.timedelta(days=6)),
        ]
        targets = list(get_targets(delta=relativedelta(days=-7)))
        assert_equal(records[1]._id, targets[0]._id)
        assert_not_in(records[0], targets)

    @mock.patch('scripts.refresh_box_tokens.Box.refresh_oauth_key')
    def test_refresh(self, mock_refresh):
        fake_account = factories.BoxAccountFactory(expires_at=datetime.datetime.utcnow())
        main(delta=relativedelta(days=7), dry_run=False)
        mock_refresh.assert_called_once()
