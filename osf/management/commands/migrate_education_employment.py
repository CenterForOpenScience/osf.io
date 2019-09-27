import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

from framework.celery_tasks import app as celery_app
from osf.models import UserEducation, UserEmployment
from osf.models.base import generate_object_id

logger = logging.getLogger(__name__)


def populate_new_models(rows, dry_run):

    set_models(dry_run, 'schools')
    set_models(dry_run, 'jobs')


def parse_model_datetime(month, year):
    return datetime.datetime.strptime('{} {}'.format(month, year), '%m %Y')


def get_dates(entry):
    start_year = entry.get('startYear', None)
    start_month = entry['startMonth'] if start_year else None
    if start_year and start_month:
        start_date = parse_model_datetime(start_month, start_year)
    else:
        start_date = None

    end_year = entry.get('endYear', None)
    end_month = entry['endMonth'] if end_year else None
    if end_year and end_month:
        end_date = parse_model_datetime(end_month, end_year)
    else:
        end_date = None

    return start_date, end_date


def set_models(dry_run, info_type):
    table = 'osf_usereducation' if info_type == 'schools' else 'osf_useremployment'
    title_or_degree = 'degree' if info_type == 'schools' else 'title'
    with connection.cursor() as cursor:
        cursor.execute("""select
        user_{info_type}.id,
                 education_items->>'ongoing' as ongoing,
                 to_date((education_items->>'startMonth'::text) || '-' || (education_items->>'startYear'::text), 'mm-yyyy') as start_date,
                 case when education_items->>'ongoing'='true' then null else to_date((education_items->>'endMonth'::text) || '-' || (education_items->>'endYear'::text), 'mm-yyyy') end as end_date,
                 education_items->>'{title_or_degree}'::text as {title_or_degree},
                 education_items->>'department' as department,
                 education_items->>'institution' as institution

          from (select users.id, jsonb_array_elements(users.{info_type}) as education_items from osf_osfuser users where users.{info_type} != '[]') as user_{info_type};""".format(info_type=info_type, title_or_degree=title_or_degree))

        data = cursor.fetchall()
        if not data:
            return
        user_id = data[0][0]
        order = 0
        for info in data:

            # update order
            if user_id == info[0]:
                order += 1
            else:
                user_id = info[0]
                order = 0

            info = [generate_object_id(), order] + list(info)
            query = """INSERT INTO {table} ( _id, _order, user_id, ongoing, start_date, end_date,  {title_or_degree}, department, institution, created, modified) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())"""
            if not dry_run:
                cursor.execute(query.format(table=table, title_or_degree=title_or_degree), info)

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
        education_queryset = UserEducation.objects.raw('''SELECT * From osf_usereducation LIMIT %s''', [rows])
        if not dry_run:
            reset_field_content(education_queryset, 'schools', dry_run)

    if employment:
        users_with_employment = UserEmployment.objects.raw('''SELECT * From osf_useremployment LIMIT %s''', [rows])
        if not dry_run:
            reset_field_content(users_with_employment, 'jobs', dry_run)


@celery_app.task(name='management.commands.migrate_employment_education')
def migrate_employment_education(
        dry_run=False,
        rows=10000,
        reverse=False,
):
    script_start_time = datetime.datetime.now()
    logger.info('Script started time: {}'.format(script_start_time))

    if reverse:
        put_jobs_and_schools_back(rows, dry_run)
    else:
        populate_new_models(rows, dry_run)

    script_finish_time = datetime.datetime.now()
    logger.info('Script finished time: {}'.format(script_finish_time))
    logger.info('Run time {}'.format(script_finish_time - script_start_time))


class Command(BaseCommand):
    help = '''This migrates user employment and education data from JSON dicts on the OSFUser model to fields
    UserEducation and UserEmployment models.'''

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

    def handle(self, *args, **options):
        logger.debug(options)

        dry_run = options['dry_run']
        rows = options['rows']
        reverse = options['reverse']
        logger.debug(
            'Dry run: {}, rows: {}, reverse: {}'.format(
                dry_run,
                rows,
                reverse
            )
        )
        if dry_run:
            logger.info('DRY RUN')

        migrate_employment_education(dry_run, rows, reverse)
