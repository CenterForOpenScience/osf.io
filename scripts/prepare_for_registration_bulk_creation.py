import logging

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from framework.celery_tasks import app as celery_app
from website.app import setup_django
setup_django()

from osf.models import OSFUser, RegistrationProvider, RegistrationBulkUploadJob, \
                       RegistrationBulkUploadRow, RegistrationSchema
from osf.models.registration_bulk_upload_job import JobState
# from website import mails

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@celery_app.task(name='scripts.prepare_for_registration_bulk_creation')
def prepare_for_registration_bulk_creation(payload_hash, initiator_id, provider_id, parsing_output, dry_run=False):

    logger.info('Preparing OSF database for registration bulk creation ...')
    initiator = OSFUser.load(initiator_id)
    if not initiator:
        logger.error('Initiator not found: [id={}]'.format(initiator_id))
        return handle_error(initiator, inform_product=True)

    try:
        provider = RegistrationProvider.objects.get(_id=provider_id)
    except RegistrationProvider.DoesNotExist or RegistrationProvider.MultipleObjectsReturned:
        logger.error('Registration provider not found or multiple results returned: [_id={}] '.format(provider_id))
        return handle_error(initiator, inform_product=True)

    if not parsing_output:
        logger.error('Missing task input: `parsing_output`')
        return handle_error(initiator, inform_product=True)

    schema_id = parsing_output.get('schema_id', None)
    try:
        schema = RegistrationSchema.objects.get(_id=schema_id)
    except RegistrationProvider.DoesNotExist or RegistrationProvider.MultipleObjectsReturned:
        logger.error('Registration schema not found or multiple results returned: [_id={}] '.format(schema_id))
        return handle_error(initiator, inform_product=True)

    upload = RegistrationBulkUploadJob.create(payload_hash, initiator, provider, schema)
    logger.info('Inserting the bulk upload job [hash={}] into table '
                'RegistrationBulkUploadJob ...'.format(upload.payload_hash))
    if not dry_run:
        try:
            upload.save()
        except ValidationError as e:
            logger.error('Insertion failed: [error={}, message={}]'.format(type(e), e.messages))
            return handle_error(initiator, inform_product=True)
        upload.reload()
        logger.info('Insertion successful: [pk={}, hash={}] '.format(upload.id, upload.payload_hash))
    else:
        logger.info('Dry run: insertion not saved')

    registration_rows = parsing_output.get('registrations', [])
    if not registration_rows:
        logger.error('Missing registration rows')
        return handle_error(initiator, inform_product=True)

    logger.info('Preparing [{}] registration rows for bulk creation ...'.format(len(registration_rows)))
    bulk_upload_rows = []
    for registration_row in registration_rows:
        bulk_upload_row = RegistrationBulkUploadRow(upload=upload, draft_registration=None, is_completed=False,
                                                    is_picked_up=False, csv_raw=registration_row.get('csv_raw', ''),
                                                    csv_parsed=registration_row.get('csv_parsed'))
        bulk_upload_rows.append(bulk_upload_row)

    if dry_run:
        logger.info('Dry run: bulk insertion not run')
        logger.info("Dry run: complete")
        return

    try:
        logger.info('Bulk inserting [{}] registration rows into table '
                    'RegistrationBulkUploadRow ...'.format(len(bulk_upload_rows)))
        created_objects = RegistrationBulkUploadRow.objects.bulk_create(bulk_upload_rows)
    except (ValueError, IntegrityError) as e:
        logger.error('Bulk insertion failed: [error={}, cause=\n{}\n]'.format(type(e), e.__cause__))
        return handle_error(initiator, inform_product=True)
    logger.info('[{}] rows successfully inserted.'.format(len(created_objects)))

    logger.info('Updating job state ...')
    upload.state = JobState.INITIALIZED
    try:
        upload.save()
    except ValidationError as e:
        logger.error('Job state update failed: [error={}, message={}]'.format(type(e), e.messages))
        return handle_error(initiator, inform_product=True)
    logger.info('Job state updated')
    upload.reload()
    logger.info('Preparation has been successfully finished: [upload_id={}, provider_id={}, schema_id={}, '
                'initiator_id={}]'.format(upload.id, upload.provider._id, upload.schema._id, upload.initiator._id))


def handle_error(initiator, inform_product=False):
    """Send emails information OSF product owner and/or registration admin about failures.
    """

    if inform_product:
        # mails.send_mail(
        #     to_addr=website_settings.Registration_Product_Owner_Email,
        #     mail=mails.REGISTRATION_BULK_UPLOAD_PRODUCT_OWNER
        # )
        pass

    if initiator:
        # mails.send_mail(
        #     to_addr=initiator.username,
        #     mail=mails.REGISTRATION_BULK_UPLOAD_REGISTRATION_ADMIN,
        #     user=initiator,
        #     osf_support_email=website_settings.OSF_SUPPORT_EMAIL
        # )
        pass
