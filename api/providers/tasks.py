import logging

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from framework.celery_tasks import app as celery_app
from framework import sentry
from osf.models import OSFUser, RegistrationProvider, RegistrationBulkUploadJob, \
                       RegistrationBulkUploadRow, RegistrationSchema
from osf.models.registration_bulk_upload_job import JobState
from website import mails, settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@celery_app.task()
def prepare_for_registration_bulk_creation(payload_hash, initiator_id, provider_id, parsing_output, dry_run=False):

    logger.info('Preparing OSF DB for registration bulk creation ...')
    initiator = OSFUser.load(initiator_id)
    if not initiator:
        message = 'Initiator not found: [id={}]'.format(initiator_id)
        return handle_error(initiator, inform_product=True, error_message=message)

    try:
        provider = RegistrationProvider.objects.get(_id=provider_id)
    except RegistrationProvider.DoesNotExist:
        message = 'Registration provider not found: [_id={}] '.format(provider_id)
        return handle_error(initiator, inform_product=True, error_message=message)
    except RegistrationProvider.MultipleObjectsReturned:
        message = 'Multiple registration providers returned: [_id={}] '.format(provider_id)
        return handle_error(initiator, inform_product=True, error_message=message)

    if not parsing_output:
        message = 'Missing task input: `parsing_output`'
        return handle_error(initiator, inform_product=True, error_message=message)

    schema_id = parsing_output.get('schema_id', None)
    try:
        schema = RegistrationSchema.objects.get(_id=schema_id)
    except RegistrationSchema.DoesNotExist:
        message = 'Registration schema not found: [_id={}] '.format(schema_id)
        return handle_error(initiator, inform_product=True, error_message=message)
    except RegistrationSchema.MultipleObjectsReturned:
        message = 'Multiple registration schemas returned: [_id={}] '.format(schema_id)
        return handle_error(initiator, inform_product=True, error_message=message)

    upload = RegistrationBulkUploadJob.create(payload_hash, initiator, provider, schema)
    logger.info('Creating a registration bulk upload job with [hash={}] ...'.format(upload.payload_hash))
    if not dry_run:
        try:
            upload.save()
        except ValidationError as e:
            message = 'Insertion failed: [hash={}, error={}, msg={}]'.format(upload.payload_hash, type(e), e.messages)
            return handle_error(initiator, inform_product=True, error_message=message)
        upload.reload()
        logger.info('Insertion successful: [pk={}, hash={}] '.format(upload.id, upload.payload_hash))
    else:
        logger.info('Dry run: insertion did not happen')

    registration_rows = parsing_output.get('registrations', [])
    if not registration_rows:
        message = 'Missing registration rows'
        return handle_error(initiator, inform_product=True, error_message=message)

    logger.info('Preparing [{}] registration rows for bulk creation ...'.format(len(registration_rows)))
    bulk_upload_rows = []
    for registration_row in registration_rows:
        bulk_upload_row = RegistrationBulkUploadRow(upload=upload, draft_registration=None, is_completed=False,
                                                    is_picked_up=False, csv_raw=registration_row.get('csv_raw', ''),
                                                    csv_parsed=registration_row.get('csv_parsed'))
        bulk_upload_rows.append(bulk_upload_row)

    if dry_run:
        logger.info('Dry run: bulk insertion not run')
        logger.info('Dry run: complete')
        return

    try:
        logger.info('Bulk creating [{}] registration bulk upload rows ...'.format(len(bulk_upload_rows)))
        created_objects = RegistrationBulkUploadRow.objects.bulk_create(bulk_upload_rows)
    except (ValueError, IntegrityError) as e:
        message = 'Bulk insertion failed: [error={}, cause={}]'.format(type(e), e.__cause__)
        return handle_error(initiator, inform_product=True, error_message=message)
    logger.info('[{}] rows successfully inserted.'.format(len(created_objects)))

    logger.info('Updating job state ...')
    upload.state = JobState.INITIALIZED
    try:
        upload.save()
    except ValidationError as e:
        message = 'Job state update failed: [error={}, message={}]'.format(type(e), e.messages)
        return handle_error(initiator, inform_product=True, error_message=message)
    logger.info('Job state updated')
    logger.info('Preparation finished: [upload={}, provider={}, schema={}, '
                'initiator={}]'.format(upload.id, upload.provider._id, upload.schema._id, upload.initiator._id))


def handle_error(initiator, inform_product=False, error_message=None):
    """Send emails information OSF product owner and/or registration admin about failures.
    """

    if error_message:
        logger.error(error_message)
        sentry.log_message(error_message)

    if inform_product:
        mails.send_mail(
            to_addr=settings.PRODUCT_OWNER_EMAIL_ADDRESS.get('Registration'),
            mail=mails.REGISTRATION_BULK_UPLOAD_PRODUCT_OWNER
        )

    if initiator:
        mails.send_mail(
            to_addr=initiator.username,
            mail=mails.REGISTRATION_BULK_UPLOAD_INITIATOR_FAILED_ON_HOLD,
            user=initiator,
            osf_support_email=settings.OSF_SUPPORT_EMAIL
        )
