import pytest
from unittest import mock
import datetime as dt
from django.utils import timezone
from tests.base import OsfTestCase

from framework.celery_tasks import handlers
from website import settings
from website.project.signals import contributor_added
from website.project.views.contributor import notify_added_contributor
from website.util.metrics import OsfSourceTags
from framework.auth import Auth

from osf_tests.factories import (
    UserFactory,
    UnconfirmedUserFactory,
    ProjectFactory,
    UnregUserFactory,
    ExternalAccountFactory,
)
from importlib import import_module
from django.conf import settings as django_conf_settings
from osf.models import UserSessionMap
from tests.utils import run_celery_tasks
from waffle.testutils import override_flag
from osf.features import ENABLE_GV

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


@pytest.mark.enable_implicit_clean
@pytest.mark.enable_bookmark_creation
class TestUserMerging(OsfTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        with self.context:
            handlers.celery_before_request()

    def _add_unconfirmed_user(self):
        self.unconfirmed = UnconfirmedUserFactory()

        self.user.add_system_tag('user')
        self.user.add_system_tag('shared')
        self.unconfirmed.add_system_tag('unconfirmed')
        self.unconfirmed.add_system_tag('shared')

    def _add_unregistered_user(self):
        self.unregistered = UnregUserFactory()

        self.project_with_unreg_contrib = ProjectFactory()
        self.project_with_unreg_contrib.add_unregistered_contributor(
            fullname='Unreg',
            email=self.unregistered.username,
            auth=Auth(self.project_with_unreg_contrib.creator)
        )
        self.project_with_unreg_contrib.save()

    @pytest.mark.enable_enqueue_task
    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_merge(self, mock_get_mailchimp_api):
        def is_mrm_field(value):
            return 'RelatedManager' in str(value.__class__)

        other_user = UserFactory()
        other_user.save()

        # create session for other_user
        other_user_session = SessionStore()
        other_user_session.create()
        UserSessionMap.objects.create(user=other_user, session_key=other_user_session.session_key)

        # define values for users' fields
        today = timezone.now()
        yesterday = today - dt.timedelta(days=1)

        self.user.comments_viewed_timestamp['shared_gt'] = today
        other_user.comments_viewed_timestamp['shared_gt'] = yesterday
        self.user.comments_viewed_timestamp['shared_lt'] = yesterday
        other_user.comments_viewed_timestamp['shared_lt'] = today
        self.user.comments_viewed_timestamp['user'] = yesterday
        other_user.comments_viewed_timestamp['other'] = yesterday

        self.user.email_verifications = {'user': {'email': 'a'}}
        other_user.email_verifications = {'other': {'email': 'b'}}

        self.user.notifications_configured = {'abc12': True}
        other_user.notifications_configured = {'123ab': True}

        self.user.external_accounts.add(ExternalAccountFactory())
        other_user.external_accounts.add(ExternalAccountFactory())

        self.user.mailchimp_mailing_lists = {
        }
        other_user.mailchimp_mailing_lists = {
            settings.MAILCHIMP_GENERAL_LIST: True
        }

        self.user.security_messages = {
            'user': today,
            'shared': today,
        }
        other_user.security_messages = {
            'other': today,
            'shared': today,
        }

        self.user.add_system_tag('user')
        self.user.add_system_tag('shared')
        other_user.add_system_tag('other')
        other_user.add_system_tag('shared')

        self.user.save()
        other_user.save()

        # define expected behavior for ALL FIELDS of the User object
        default_to_master_user_fields = [
            'id',
            'date_confirmed',
            'date_disabled',
            'date_last_login',
            'date_registered',
            'email_last_sent',
            'external_identity',
            'family_name',
            'fullname',
            'given_name',
            'is_invited',
            'is_registered',
            'jobs',
            'locale',
            'merged_by',
            'middle_names',
            'password',
            'schools',
            'social',
            'suffix',
            'timezone',
            'username',
            'verification_key',
            'verification_key_v2',
            'contributor_added_email_records',
            'requested_deactivation',
        ]

        calculated_fields = {
            'comments_viewed_timestamp': {
                'user': yesterday,
                'other': yesterday,
                'shared_gt': today,
                'shared_lt': today,
            },
            'email_verifications': {
                'user': {'email': 'a'},
                'other': {'email': 'b'},
            },
            'notifications_configured': {
                '123ab': True, 'abc12': True,
            },
            'emails': {
                other_user.emails.first().id,
                self.user.emails.first().id,
            },
            'external_accounts': {
                self.user.external_accounts.first().id,
                other_user.external_accounts.first().id,
            },
            'recently_added': set(),
            'mailchimp_mailing_lists': {
                settings.MAILCHIMP_GENERAL_LIST: True
            },
            'osf_mailing_lists': {
                'Open Science Framework Help': True
            },
            'security_messages': {
                'user': today,
                'other': today,
                'shared': today,
            },
            'unclaimed_records': {},
        }

        # from the explicit rules above, compile expected field/value pairs
        expected = {}
        expected.update(calculated_fields)
        for key in default_to_master_user_fields:
            if is_mrm_field(getattr(self.user, key)):
                expected[key] = set(list(getattr(self.user, key).all().values_list('id', flat=True)))
            else:
                expected[key] = getattr(self.user, key)

        # ensure all fields of the user object have an explicit expectation
        all_field_names = {each.name for each in self.user._meta.get_fields()}
        assert set(expected.keys()).issubset(all_field_names)

        # mock mailchimp
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client

        with run_celery_tasks():
            # perform the merge
            with override_flag(ENABLE_GV, active=True):
                self.user.merge_user(other_user)
            self.user.save()

        self.user.reload()

        # check each field/value pair
        for k, v in expected.items():
            if is_mrm_field(getattr(self.user, k)):
                assert set(list(getattr(self.user, k).all().values_list('id', flat=True))) == v, f'{k} doesn\'t match expectations'
            else:
                assert getattr(self.user, k) == v, f'{k} doesn\'t match expectation'

        assert sorted(self.user.system_tags) == ['other', 'shared', 'user']

        # check fields set on merged user
        assert other_user.merged_by == self.user

        assert not SessionStore().exists(session_key=other_user_session.session_key)

    def test_merge_unconfirmed(self):
        self._add_unconfirmed_user()
        unconfirmed_username = self.unconfirmed.username
        with override_flag(ENABLE_GV, active=True):
            self.user.merge_user(self.unconfirmed)

        assert self.unconfirmed.is_merged is True
        assert self.unconfirmed.merged_by == self.user

        assert self.user.is_registered is True
        assert self.user.is_invited is False

        assert sorted(self.user.system_tags) == sorted(['shared', 'user', 'unconfirmed', OsfSourceTags.Osf.value])

        assert self.unconfirmed.email_verifications == {}
        assert self.unconfirmed.password[0] == '!'
        assert self.unconfirmed.verification_key is None
        # The mergee's email no longer needs to be confirmed by merger
        unconfirmed_emails = [record['email'] for record in self.user.email_verifications.values()]
        assert unconfirmed_username not in unconfirmed_emails

    def test_merge_preserves_external_identity(self):
        verified_user = UserFactory(external_identity={'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}})
        linking_user = UserFactory(external_identity={'ORCID': {'1234-1234-1234-1234': 'LINK'}})
        creating_user = UserFactory(external_identity={'ORCID': {'1234-1234-1234-1234': 'CREATE'}})
        different_id_user = UserFactory(external_identity={'ORCID': {'4321-4321-4321-4321': 'VERIFIED'}})
        no_id_user = UserFactory(external_identity={'ORCID': {}})
        no_provider_user = UserFactory(external_identity={})

        with override_flag(ENABLE_GV, active=True):
            linking_user.merge_user(creating_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'LINK'}}

        with override_flag(ENABLE_GV, active=True):
            linking_user.merge_user(verified_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}}
        with override_flag(ENABLE_GV, active=True):
            linking_user.merge_user(no_id_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}}
        with override_flag(ENABLE_GV, active=True):
            linking_user.merge_user(no_provider_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED'}}
        with override_flag(ENABLE_GV, active=True):
            linking_user.merge_user(different_id_user)
        assert linking_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED', '4321-4321-4321-4321': 'VERIFIED'}}

        assert creating_user.external_identity == {}
        assert verified_user.external_identity == {}
        assert no_id_user.external_identity == {}
        assert no_provider_user.external_identity == {}

        with override_flag(ENABLE_GV, active=True):
            no_provider_user.merge_user(linking_user)
        assert linking_user.external_identity == {}
        assert no_provider_user.external_identity == {'ORCID': {'1234-1234-1234-1234': 'VERIFIED', '4321-4321-4321-4321': 'VERIFIED'}}

    def test_merge_unregistered(self):
        # test only those behaviors that are not tested with unconfirmed users
        self._add_unregistered_user()

        with override_flag(ENABLE_GV, active=True):
            self.user.merge_user(self.unregistered)

        self.project_with_unreg_contrib.reload()
        assert self.user.is_invited is True
        assert self.user in self.project_with_unreg_contrib.contributors

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_merge_doesnt_send_signal(self, mock_notify):
        #Explictly reconnect signal as it is disconnected by default for test
        contributor_added.connect(notify_added_contributor)
        other_user = UserFactory()
        with override_flag(ENABLE_GV, active=True):
            self.user.merge_user(other_user)
        assert other_user.merged_by._id == self.user._id
        assert mock_notify.called is False
