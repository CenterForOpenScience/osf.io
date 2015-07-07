import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import RegistrationFactory, UserFactory

from website import models

from scripts.email_registration_contributors import (
    get_registration_contributors, send_retraction_and_embargo_addition_message,
    main, MAILER, MESSAGE_NAME
)


class TestSendRetractionAndEmbargoAdditionMessage(OsfTestCase):

    def setUp(self):
        super(TestSendRetractionAndEmbargoAdditionMessage, self).setUp()
        self.registration_contrib = UserFactory()
        self.other_user = UserFactory()
        self.registration = RegistrationFactory(creator=self.registration_contrib)

    def tearDown(self):
        super(TestSendRetractionAndEmbargoAdditionMessage, self).tearDown()
        models.Node.remove()
        models.User.remove()

    def test_get_registration_contributors(self):
        assert_equal(models.User.find().count(), 2)
        registration_contributors = get_registration_contributors()
        assert_equal(len(registration_contributors), 1)

    @mock.patch('scripts.email_registration_contributors.send_retraction_and_embargo_addition_message')
    def test_send_retraction_and_embargo_addition_message(self, mock_send_mail):
        user = UserFactory()
        send_retraction_and_embargo_addition_message(user, MESSAGE_NAME, MAILER, dry_run=False)
        user.reload()
        assert_in(MESSAGE_NAME, user.security_messages)

    @mock.patch('scripts.email_registration_contributors.send_retraction_and_embargo_addition_message')
    def test_dry_run_does_not_save_to_user(self, mock_send_mail):
        user = UserFactory()
        send_retraction_and_embargo_addition_message(user, MESSAGE_NAME, MAILER, dry_run=True)
        user.reload()
        assert_not_in(MESSAGE_NAME, user.security_messages)

    def test_main_dry_run_True_does_save(self):
        assert_equal(len(get_registration_contributors()), 1)
        main(dry_run=False)
        assert_equal(len(get_registration_contributors()), 0)

    def test_main_dry_run_False_does_not_save(self):
        assert_equal(len(get_registration_contributors()), 1)
        main(dry_run=True)
        assert_equal(len(get_registration_contributors()), 1)
