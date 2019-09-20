import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

from framework import sentry
from framework.celery_tasks import app as celery_app
from osf.models import OSFUser, UserEducation, UserEmployment

logger = logging.getLogger(__name__)


DATE_FIELDS = ['startMonth', 'startYear', 'endMonth', 'endYear']

# Sample queries to pull data out of the json blob. This can be used for the migration to hopefully speed things up
# considerably.
#
# select user_schools.id,
#        education_items->>'startMonth' as start_month,
#        education_items->>'startYear' as start_year,
#        to_date((education_items->>'startMonth'::text) || '-' || (education_items->>'startYear'::text), 'mm-yyyy') as start_date,
#        education_items->>'ongoing' as ongoing,
#        education_items->>'endMonth' as end_month,
#        education_items->>'endYear' as end_year,
#        case when education_items->>'ongoing'='true' then null else to_date((education_items->>'endMonth'::text) || '-' || (education_items->>'endYear'::text), 'mm-yyyy') end as end_date,
#        education_items->>'degree' as degree,
#        education_items->>'department' as department,
#        education_items->>'institution' as institution
#
# from (select users.id, jsonb_array_elements(users.schools) as education_items from osf_osfuser users where users.schools != '[]') as user_schools;
#
# select user_jobs.id,
#        employment_items->>'startMonth' as start_month,
#        employment_items->>'startYear' as start_year,
#        to_date((employment_items->>'startMonth'::text) || '-' || (employment_items->>'startYear'::text), 'mm-yyyy') as start_date,
#        employment_items->>'ongoing' as ongoing,
#        employment_items->>'endMonth' as end_month,
#        employment_items->>'endYear' as end_year,
#        case when employment_items->>'ongoing'='true' then null else to_date((employment_items->>'endMonth'::text) || '-' || (employment_items->>'endYear'::text), 'mm-yyyy') end as end_date,
#        employment_items->>'title' as title,
#        employment_items->>'department' as department,
#        employment_items->>'institution' as institution
#
# from (select users.id, jsonb_array_elements(users.jobs) as employment_items from osf_osfuser users where users.jobs != '[]') as user_jobs;


def populate_new_models(rows, dry_run, education, employment):
    if education:
        users_with_education = OSFUser.objects.exclude(schools=[]).limit(rows)
        set_model_content(UserEducation, users_with_education, 'schools', dry_run)

    if employment:
        users_with_employment = OSFUser.objects.exclude(jobs=[]).limit(rows)
        set_model_content(UserEmployment, users_with_employment, 'jobs', dry_run)


def parse_model_datetime(month, year):
    try:
        parsed = datetime.strptime('{} {}'.format(month, year), '%m %Y')
    except ValueError:
        parsed = datetime.strptime('{} {}'.format(month, year), '%m %y')
    except ValueError:
        parsed = None
    return parsed


def set_model_content(model, queryset, original_attribute, dry_run):
    for user in queryset:
        original_entries = getattr(user, original_attribute)
        for entry in original_entries:
            institution = entry.get('institution')
            if institution:
                new_object = model(
                    user=user,
                    institution=institution
                )
                for key, value in entry.items():
                    if key != 'institution' and key not in DATE_FIELDS:
                        setattr(new_object, key, value)

                start_year = entry.get('startYear', None)
                start_month = entry['startMonth'] if start_year else None
                if start_year and start_month:
                    new_object.start_date = parse_model_datetime(start_month, start_year)

                end_year = entry.get('endYear', None)
                end_month = entry['endMonth'] if end_year else None
                if end_year and end_month:
                    new_object.end_date = parse_model_datetime(end_month, end_year)
                if dry_run:
                    logger.info('Model: {}'.format(new_object))
                else:
                    new_object.save()


def reset_field_content(queryset, original_attribute, dry_run):
    for entry in queryset:
        user = entry.user
        start_date = entry.start_date
        end_date = entry.end_date
        attributes = {
            'institution': entry.institution,
            'startYear': start_date.year if start_date else None,
            'startMonth': start_date.month if start_date else None,
            'endYear': end_date.year if end_date else None,
            'endMonth': end_date.month if end_date else None,
            'department': entry.department,
            'ongoing': entry.ongoing,
        }
        if original_attribute == 'schools':
            attributes['degree'] = entry.degree
        elif original_attribute == 'jobs':
            attributes['title'] = entry.title

        user_entries = getattr(user, original_attribute, [])
        user_entries.append(attributes)
        if dry_run:
            logger.info('User: {}, attributes: {}'.format(user, attributes))
        else:
            setattr(user, original_attribute, user_entries)
            user.save()


def put_jobs_and_schools_back(rows, dry_run, education, employment):
    if education:
        education_queryset = UserEducation.objects.all().limit(rows)
        if not dry_run:
            reset_field_content(education_queryset, 'schools', dry_run)
    if employment:
        employment_queryset = UserEmployment.objects.all().limit(rows)
        if not dry_run:
            reset_field_content(employment_queryset, 'jobs', dry_run)


@celery_app.task(name='management.commands.migrate_employment_education')
def migrate_employment_education(
        dry_run=False,
        rows=10000,
        reverse=False,
        education=True,
        employment=True
):
    script_start_time = datetime.datetime.now()
    logger.info('Script started time: {}'.format(script_start_time))

    if reverse:
        put_jobs_and_schools_back(rows, dry_run, education,employment)
    else:
        populate_new_models(rows, dry_run, education,employment)

    script_finish_time = datetime.datetime.now()
    logger.info('Script finished time: {}'.format(script_finish_time))
    logger.info('Run time {}'.format(script_finish_time - script_start_time))


class Command(BaseCommand):
    help = '''Does the work of the pagecounter migration so that it can be done incrementally when convenient.
    You will either need to set the page_size large enough to get all of the records, or you will need to run the
    script multiple times until it tells you that it is done.'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Run queries but do not write files',
        )
        parser.add_argument(
            '--rows',
            type=int,
            default=10000,
            help='How many rows to process during this run',
        )
        parser.add_argument(
            '--reverse',
            type=bool,
            default=False,
            help='Reverse out the migration',
        )
        parser.add_argument(
            '--education',
            type=bool,
            default=True,
            help='Populate education fields',
        )
        parser.add_argument(
            '--employment',
            type=bool,
            default=True,
            help='Populate employment fields',
        )

    # Management command handler
    def handle(self, *args, **options):
        logger.debug(options)

        dry_run = options['dry_run']
        rows = options['rows']
        reverse = options['reverse']
        education = options['education']
        employment = options['employment']
        logger.debug(
            'Dry run: {}, rows: {}, reverse: {}, education: {}, employment: {}'.format(
                dry_run,
                rows,
                reverse,
                education,
                employment,
            )
        )
        if dry_run:
            logger.info('DRY RUN')

        migrate_employment_education(dry_run, rows, reverse, education, employment)
