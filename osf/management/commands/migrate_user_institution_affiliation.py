import datetime
import logging

from django.core.management.base import BaseCommand

from osf.models import Institution, InstitutionAffiliation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Update emails of users from a given affiliated institution (when eligible).
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='If true, iterate through eligible users and institutions only'
        )

    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info(f'Script started time: {script_start_time}')

        dry_run = options.get('dry_run', False)
        if dry_run:
            logger.warning('Dry Run: This is a dry-run pass!')
        migrate_user_institution_affiliation(dry_run=dry_run)

        script_finish_time = datetime.datetime.now()
        logger.info(f'Script finished time: {script_finish_time}')
        logger.info(f'Run time {script_finish_time - script_start_time}')


def migrate_user_institution_affiliation(dry_run=True):

    institutions = Institution.objects.get_all_institutions()
    institution_total = institutions.count()

    institution_count = 0
    user_count = 0
    skipped_user_count = 0

    for institution in institutions:
        institution_count += 1
        user_count_per_institution = 0
        skipped_user_count_per_institution = 0
        users = institution.osfuser_set.all()
        user_total_per_institution = users.count()
        sso_identity = None
        if not institution.delegation_protocol:
            sso_identity = InstitutionAffiliation.DEFAULT_VALUE_FOR_SSO_IDENTITY_NOT_AVAILABLE
        logger.info(f'Migrating affiliation for <{institution.name}> [{institution_count}/{institution_total}]')
        for user in institution.osfuser_set.all():
            user_count_per_institution += 1
            user_count += 1
            logger.info(f'\tMigrating affiliation for <{user._id}::{institution.name}> '
                        f'[{user_count_per_institution}/{user_total_per_institution}]')
            if not dry_run:
                affiliation = user.add_or_update_affiliated_institution(
                    institution,
                    sso_identity=sso_identity,
                    sso_department=user.department
                )
                if affiliation:
                    logger.info(f'\tAffiliation=<{affiliation}> migrated or updated '
                                f'for user=<{user._id}> @ institution=<{institution._id}>')
                else:
                    skipped_user_count_per_institution += 1
                    skipped_user_count += 1
                    logger.info(f'\tSkip migration or update since affiliation exists '
                                f'for user=<{user._id}> @ institution=<{institution._id}>')
            else:
                logger.warning(f'\tDry Run: Affiliation not migrated for {user._id} @ {institution._id}!')
        if user_count_per_institution == 0:
            logger.warning('No eligible user found')
        else:
            logger.info(f'Finished migrating affiliation for {user_count_per_institution} users '
                        f'@ <{institution.name}>, including {skipped_user_count_per_institution} skipped users')
    logger.info(f'Finished migrating affiliation for {user_count} users @ {institution_count} institutions, '
                f'including {skipped_user_count} skipped users')
