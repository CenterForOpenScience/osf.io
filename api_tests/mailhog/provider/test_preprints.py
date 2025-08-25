from waffle.testutils import override_switch
from osf import features

from framework.auth.core import Auth
from osf.models import NotificationType
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
)
from osf.utils.permissions import WRITE
from tests.base import OsfTestCase
from tests.utils import get_mailhog_messages, delete_mailhog_messages, capture_notifications, assert_emails


class TestPreprintConfirmationEmails(OsfTestCase):
    passthrough_notifications = True

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.write_contrib = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.preprint = PreprintFactory(creator=self.user, project=self.project, provider=PreprintProviderFactory(_id='osf'), is_published=False)
        self.preprint.add_contributor(self.write_contrib, permissions=WRITE)
        self.preprint_branded = PreprintFactory(creator=self.user, is_published=False)

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_creator_gets_email(self):
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            self.preprint.set_published(True, auth=Auth(self.user), save=True)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            self.preprint_branded.set_published(True, auth=Auth(self.user), save=True)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()
