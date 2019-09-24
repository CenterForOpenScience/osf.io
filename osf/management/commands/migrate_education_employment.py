import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

from framework.celery_tasks import app as celery_app
from osf.models import OSFUser, UserEducation, UserEmployment
from osf.models.base import generate_object_id

logger = logging.getLogger(__name__)


def populate_new_models(rows, dry_run):

    users_with_education = OSFUser.objects.raw('''SELECT id, schools FROM osf_osfuser where schools <> '{}' LIMIT %s''', [rows])
    set_model(users_with_education, 'schools', dry_run)

    users_with_employment = OSFUser.objects.raw('''SELECT id, jobs FROM osf_osfuser where jobs <> '{}' LIMIT %s''', [rows])
    set_model(users_with_employment, 'jobs', dry_run)


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


def set_model(queryset, attribute_name, dry_run):
    if attribute_name == 'schools':
        query = 'INSERT INTO osf_usereducation (_id, user_id, ongoing, degree, department, institution, end_date, start_date, created, modified, _order) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

    if attribute_name == 'jobs':
        query = 'INSERT INTO osf_useremployment (_id, user_id, ongoing, title, department, institution, end_date, start_date, created, modified, _order) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

    with connection.cursor() as cursor:
        for user in queryset:
            entry = getattr(user, attribute_name)
            for order, data in enumerate(entry):
                start_date, end_date = get_dates(data)
                ongoing = data.get('ongoing')
                title_or_degree = data.get('title') or data.get('degree')
                department = data.get('department')
                institution = data.get('institution')
                created = datetime.datetime.now()

                if dry_run:
                    logger.info('dry_run')
                else:
                    sql_params = [
                        generate_object_id(),
                        user.id,
                        ongoing,
                        title_or_degree,
                        department,
                        institution,
                        end_date,
                        start_date,
                        created,
                        created,
                        order
                    ]
                    cursor.execute(query, sql_params)


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
