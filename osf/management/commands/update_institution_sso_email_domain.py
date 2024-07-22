from enum import IntEnum
import logging

from django.core.management.base import BaseCommand

from framework import sentry
from framework.auth import get_user
from osf.exceptions import BlockedEmailError, ValidationError
from osf.models import Institution, OSFUser
from osf.models.validators import validate_email

logger = logging.getLogger(__name__)


class UpdateResult(IntEnum):
    """Defines 4 states of the email update outcome.
    """
    SUCCEEDED = 0  # The email has successfully been added
    SKIPPED = 1  # The email was added (to the user) before the script is run, or the eligible email is not found
    FAILED = 2  # The email failed to be added since it belongs to another account
    ERRORED = 3  # The email failed to be added due to unexpected exceptions


class Command(BaseCommand):
    """Update emails of users from a given affiliated institution (when eligible).
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            'institution_id',
            type=str,
            help='the institution whose affiliated users\' eligible email is to be updated'
        )
        parser.add_argument(
            'src_domain',
            type=str,
            help='the email domain that are eligible for update'
        )
        parser.add_argument(
            'dst_domain',
            type=str,
            help='the email domain that is to be added'
        )
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='If true, iterate through eligible users and emails but don\'t add the email'
        )

    def handle(self, *args, **options):

        institution_id = options.get('institution_id', '').lower()
        src_domain = options.get('src_domain', '').lower()
        dst_domain = options.get('dst_domain', '').lower()
        dry_run = options.get('dry_run', True)

        if dry_run:
            logger.warning('This is a dry-run pass.')

        # Verify the institution
        institution = Institution.load(institution_id)
        if not institution:
            message = f'Error: invalid institution ID [{institution_id}]'
            logger.error(message)
            sentry.log_message(message)
            return

        # Find all users affiliated with the given institution
        affiliated_users = OSFUser.objects.filter(affiliated_institutions___id=institution_id)

        # Update email domain for each user
        update_result = {
            UpdateResult.SUCCEEDED.name: {},
            UpdateResult.SKIPPED.name: {},
            UpdateResult.FAILED.name: {},
            UpdateResult.ERRORED.name: {},
        }
        for user in affiliated_users:
            user_result = update_email_domain(user, src_domain, dst_domain, dry_run=dry_run)
            if user_result.get(UpdateResult.SUCCEEDED.name):
                update_result.get(UpdateResult.SUCCEEDED.name)[user._id] = user_result.get(UpdateResult.SUCCEEDED.name)
            if user_result.get(UpdateResult.SKIPPED.name):
                update_result.get(UpdateResult.SKIPPED.name)[user._id] = user_result.get(UpdateResult.SKIPPED.name)
            if user_result.get(UpdateResult.FAILED.name):
                update_result.get(UpdateResult.FAILED.name)[user._id] = user_result.get(UpdateResult.FAILED.name)
            if user_result.get(UpdateResult.ERRORED.name):
                update_result.get(UpdateResult.ERRORED.name)[user._id] = user_result.get(UpdateResult.ERRORED.name)

        # Output update results to console
        logger.info(f'{UpdateResult.SUCCEEDED.name} = {update_result.get(UpdateResult.SUCCEEDED.name)}')
        logger.info(f'{UpdateResult.SKIPPED.name} = {update_result.get(UpdateResult.SKIPPED.name)}')
        logger.warning(f'{UpdateResult.FAILED.name} = {update_result.get(UpdateResult.FAILED.name)}')
        logger.error(f'{UpdateResult.ERRORED.name} = {update_result.get(UpdateResult.ERRORED.name)}')
        if dry_run:
            logger.warning(f'The above output is the result from a dry-run pass! '
                           f'{UpdateResult.SUCCEEDED.name} ones were not actually added!')


def update_email_domain(user, src_domain, dst_domain, dry_run=True):
    """For a given user, if it has an email `example@<src_domain>`, attempt to add `example@<dst_domain>` to this
    account. The action will be skipped if `example@<dst_domain>` already exists on this user or no email is found
    under `@<src_domain>`. The action will fail if `example@<dst_domain>` already exists on another account. Other
    unexpected exceptions will be considered as error.
    """

    # Find eligible emails to add
    emails_to_add = []
    user_result = {
        UpdateResult.SUCCEEDED.name: [],
        UpdateResult.SKIPPED.name: [],
        UpdateResult.FAILED.name: [],
        UpdateResult.ERRORED.name: [],
    }
    for email in user.emails.filter(address__endswith=f'@{src_domain}'):
        email_parts = email.address.split('@')
        name_part = email_parts[0].lower()
        domain_part = email_parts[1].lower()
        if domain_part == src_domain:
            emails_to_add.append(f'{name_part}@{dst_domain}')
    if not emails_to_add:
        logger.warning(f'Action skipped due to no eligible email found for user [{user._id}]!')
        return user_result
    # Verify and attempt to add email; keep track of successes, failures and errors
    for email in emails_to_add:
        try:
            validate_email(email)
        except (ValidationError, BlockedEmailError) as e:
            logger.error(f'Email validation failed when adding [{email}] to user [{user._id}]!')
            sentry.log_exception(e)
            user_result.get(UpdateResult.ERRORED.name).append(email)
            continue
        duplicate_user = get_user(email=email)
        if not duplicate_user:
            try:
                if not dry_run:
                    user.emails.create(address=email)
            except Exception as e:
                logger.error(f'An unexpected error occurred when adding email [{email}] to user [{user._id}]!')
                sentry.log_exception(e)
                user_result.get(UpdateResult.ERRORED.name).append(email)
            else:
                logger.info(f'Successfully added email [{email}] to user [{user._id}]!')
                user_result.get(UpdateResult.SUCCEEDED.name).append(email)
        elif duplicate_user == user:
            logger.info(f'Action skipped since email [{email}] exists for the same user [{user._id}]!')
            user_result.get(UpdateResult.SKIPPED.name).append(email)
        else:
            logger.warning(f'Action aborted since email [{email}] exists for a different user [{duplicate_user._id}]!')
            user_result.get(UpdateResult.FAILED.name).append(email)
    return user_result
