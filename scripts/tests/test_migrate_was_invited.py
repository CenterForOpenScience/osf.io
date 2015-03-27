# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

from tests.base import fake
from tests.base import OsfTestCase
from tests.factories import UserFactory
from tests.factories import NodeFactory
from tests.factories import UnconfirmedUserFactory

from framework.auth.core import Auth

from scripts.migrate_was_invited import main
from scripts.migrate_was_invited import is_invited


class TestWasInvited(OsfTestCase):

    def test_was_invited(self):
        referrer = UserFactory()
        node = NodeFactory(creator=referrer)
        name = fake.name()
        email = fake.email()
        user = node.add_unregistered_contributor(
            fullname=name,
            email=email,
            auth=Auth(user=referrer),
        )
        user.register(email, 'secret')
        assert_true(is_invited(user))
        user.is_invited = None
        user.save()
        main(dry_run=False)
        user.reload()
        assert_true(user.is_invited)

    def test_was_not_invited(self):
        referrer = UserFactory()
        node = NodeFactory(creator=referrer)
        user = UserFactory()
        node.add_contributor(user, auth=Auth(referrer))
        assert_false(is_invited(user))
        user.is_invited = None
        user.save()
        main(dry_run=False)
        user.reload()
        assert_false(user.is_invited)

    def test_was_not_invited_unconfirmed(self):
        user = UnconfirmedUserFactory()
        assert_false(is_invited(user))
        user.is_invited = None
        user.save()
        main(dry_run=False)
        user.reload()
        assert_false(user.is_invited)
