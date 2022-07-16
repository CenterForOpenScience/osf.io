import copy
import datetime as dt

from django.utils import timezone

from framework.auth import Auth

from osf.utils import permissions
from osf.models import RegistrationSchema

from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory, ProjectFactory, DraftRegistrationFactory, OSFGroupFactory

class RegistrationsTestBase(OsfTestCase):
    def setUp(self):
        super(RegistrationsTestBase, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.node = ProjectFactory(creator=self.user)
        self.non_admin = AuthUserFactory()
        self.node.add_contributor(
            self.non_admin,
            permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            auth=self.auth,
            save=True
        )
        self.non_contrib = AuthUserFactory()
        self.group_mem = AuthUserFactory()
        self.group = OSFGroupFactory(creator=self.group_mem)
        self.node.add_osf_group(self.group, permissions.ADMIN)

        self.meta_schema = RegistrationSchema.objects.get(name='Open-Ended Registration', schema_version=2)

        self.draft = DraftRegistrationFactory(
            initiator=self.user,
            branched_from=self.node,
            registration_schema=self.meta_schema,
            registration_metadata={
                'summary': {'value': 'Some airy'}
            }
        )

        current_month = timezone.now().strftime('%B')
        current_year = timezone.now().strftime('%Y')

        valid_date = timezone.now() + dt.timedelta(days=180)
        self.embargo_payload = {
            'data': {
                'attributes': {
                    'children': [self.node._id],
                    'draft_registration': self.draft._id,
                    'lift_embargo': str(valid_date.strftime('%a, %d, %B %Y %H:%M:%S')) + u' GMT',
                    'registration_choice': 'embargo',
                },
                'type': 'registrations',
            },
        }
        self.invalid_embargo_date_payload = copy.deepcopy(self.embargo_payload)
        self.invalid_embargo_date_payload['data']['attributes']['lift_embargo'] = u'Thu, 01 {month} {year} 05:00:00 GMT'.format(
            month=current_month,
            year=str(int(current_year) - 1)
        )

        self.immediate_payload = {
            'data': {
                'attributes': {
                    'children': [self.node._id],
                    'draft_registration': self.draft._id,
                    'registration_choice': 'immediate',
                },
                'type': 'registrations',
            },
        }
        self.invalid_payload = copy.deepcopy(self.immediate_payload)
        self.invalid_payload['data']['attributes']['registration_choice'] = 'foobar'

    def draft_url(self, view_name):
        return self.node.web_url_for(view_name, draft_id=self.draft._id)

    def draft_api_url(self, view_name):
        return self.node.api_url_for(view_name, draft_id=self.draft._id)
