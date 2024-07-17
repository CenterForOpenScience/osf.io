from django.utils import timezone

from osf.utils.workflows import ModerationWorkflows
from api_tests.utils import UserRoles
from osf.models import Outcome
from osf.utils.outcomes import ArtifactTypes
from osf.utils.workflows import RegistrationModerationStates as RegStates
from osf_tests.factories import (
    AuthUserFactory,
    IdentifierFactory,
    RegistrationFactory,
    RegistrationProviderFactory
)

TEST_EXTERNAL_PID = 'This is a doi'

# Omitted the following redundant states:
# PENDING_EMBARGO_TERMINATION (overlaps EMBARGO)
# PENDING_WITHDRAW_REQUEST and PENDING_WITHDRAW (overlaps ACCEPTED)
# REVERTED (overlaps REJECTED)
#
# Techncically PENDING and EMBARGO overlap as well, but worth confirming EMBARGO behavior
STATE_VISIBILITY_MAPPINGS = {
    RegStates.INITIAL: {'public': False, 'deleted': False},
    RegStates.PENDING: {'public': False, 'deleted': False},
    RegStates.EMBARGO: {'public': False, 'deleted': False},
    RegStates.ACCEPTED: {'public': True, 'deleted': False},
    RegStates.WITHDRAWN: {'public': True, 'deleted': False},
    RegStates.REJECTED: {'public': False, 'deleted': True},
    # Use the generally unreachable UNDEFINED value for the edge case of deleted and public
    RegStates.UNDEFINED: {'public': True, 'deleted': True},
}


def configure_test_preconditions(registration_state=RegStates.ACCEPTED, user_role=UserRoles.ADMIN_USER):
    provider = RegistrationProviderFactory()
    provider.update_group_permissions()
    provider.reviews_workflow = ModerationWorkflows.PRE_MODERATION.value
    provider.save()

    state_settings = STATE_VISIBILITY_MAPPINGS[registration_state]
    registration = RegistrationFactory(
        provider=provider,
        is_public=state_settings['public'],
        has_doi=True
    )
    registration.moderation_state = registration_state.db_name
    registration.deleted = timezone.now() if state_settings['deleted'] else None
    registration.save()

    outcome = Outcome.objects.for_registration(registration, create=True)
    test_artifact = outcome.artifact_metadata.create(
        identifier=IdentifierFactory(value=TEST_EXTERNAL_PID, category='doi'),
        artifact_type=ArtifactTypes.DATA,
    )

    test_auth = configure_test_auth(registration, user_role)

    return test_artifact, test_auth, registration


def configure_test_auth(registration, user_role):
    if user_role is UserRoles.UNAUTHENTICATED:
        return None

    user = AuthUserFactory()
    if user_role is UserRoles.MODERATOR:
        registration.provider.get_group('moderator').user_set.add(user)
    elif user_role in UserRoles.contributor_roles():
        registration.add_contributor(user, user_role.get_permissions_string())

    return user.auth
