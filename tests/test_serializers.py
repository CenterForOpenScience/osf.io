# -*- coding: utf-8 -*-

from nose.tools import *  # PEP8 asserts

from tests.factories import ProjectFactory, UserFactory, RegistrationFactory
from tests.base import OsfTestCase

from framework.auth import Auth
from website.project.views.node import _get_summary


class TestNodeSerializers(OsfTestCase):

    # Regression test for #489
    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_get_summary_private_node_should_include_id_and_primary_boolean(self):
        user = UserFactory()
        # user cannot see this node
        node = ProjectFactory(public=False)
        result = _get_summary(node, auth=Auth(user),
            rescale_ratio=None,
            primary=True,
            link_id=None
        )

        # serialized result should have id and primary
        assert_equal(result['summary']['id'], node._primary_key)
        assert_true(result['summary']['primary'], True)

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/668
    def test_get_summary_for_registration_uses_correct_date_format(self):
        reg = RegistrationFactory()
        res = _get_summary(reg, auth=Auth(reg.creator), rescale_ratio=None)
        assert_equal(res['summary']['registered_date'],
                    reg.registered_date.strftime('%b %d %Y %I:%M %p UTC'))
