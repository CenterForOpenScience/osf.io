import logging

from django.core.exceptions import ValidationError

from framework.celery_tasks import app as celery_app
from website.app import setup_django
setup_django()

from osf.models import OSFUser, RegistrationProvider, RegistrationBulkUpload, \
                       BulkUploadedRegistration, RegistrationSchema

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@celery_app.task(name='scripts.prepare_for_registration_bulk_creation')
def prepare_for_registration_bulk_creation(parsing_output, dry_run=False):

    if not parsing_output:
        logger.error('Missing CSV input')
        return handle_internal_error()
        # The following are temporarily hard-coded and used for local implementation/testing only. The format of
        # the `csv_input` has mostly been determined, except for the `csv_parsed` which needs collaboration with
        # the parser piece. The value of `csv_parsed` is expected to be a serializable object that can be pickled
        # and un-pickled by celery automatically.
        # parsing_output = {
        #     'payload_hash': '07eef7ee-fc69-4e3a-9047-8d0e0a4cb909',
        #     'provider_id': 'osf',
        #     'schema_id': '60f74311ed3441000141b265',
        #     'initiator_id': 't47ka',
        #     'registrations': [
        #         {
        #             'external_id': '27093472',
        #             'csv_raw': '1997,Ford,F250,Black',
        #             'csv_parsed': {
        #                 'year': 1997,
        #                 'make': 'Ford',
        #                 'model': 'F250',
        #                 'color': 'Black',
        #             },
        #         },
        #         {
        #             'external_id': '98709987',
        #             'csv_raw': '2000,Volkswagen,Golf,White',  # here goes the raw string of one row
        #             'csv_parsed': {
        #                 'year': 2000,
        #                 'make': 'Volkswagen',
        #                 'model': 'Golf',
        #                 'color': 'White',
        #             },
        #         },
        #         {
        #             'external_id': '64510752',
        #             'csv_raw': '2011,Subaru,WRX,Blue',  # here goes the raw string of
        #             'csv_parsed': {
        #                 'year': 2011,
        #                 'make': 'Subaru',
        #                 'model': 'WRX',
        #                 'color': 'Blue',
        #             },
        #         },
        #     ],
        # }

    logger.info('Preparing OSF database for registration bulk creation ...')
    initiator_id = parsing_output.get('initiator_id', None)
    if not initiator_id:
        logger.error('Missing initiator id')  # internal error
        return handle_internal_error()
    initiator = OSFUser.load(initiator_id)
    if not initiator:
        logger.error('Initiator not found: [id={}]'.format(initiator_id))  # internal error
        return handle_internal_error()

    provider_id = parsing_output.get('provider_id', None)
    if not provider_id:
        logger.error('Missing provider id')  # internal error
        return handle_internal_error()
    provider = RegistrationProvider.objects.filter(_id=provider_id).first()
    if not provider:
        logger.error('Provider not found: [id={}] '.format(provider_id))  # internal error
        return handle_internal_error()

    schema_id = parsing_output.get('schema_id', None)
    if not schema_id:
        logger.error('Missing schema id')  # internal error
        return handle_internal_error()
    schema = RegistrationSchema.objects.filter(_id=schema_id).first()
    if not schema:
        logger.error('Schema not found: [id={}] '.format(provider_id))  # internal error
        return handle_internal_error()

    upload = RegistrationBulkUpload.create(parsing_output.get('payload_hash', ''), initiator, provider, schema)
    logger.info('Inserting the bulk upload [hash={}] into the table RegistrationBulkUpload ...'.format(upload.payload_hash))
    if not dry_run:
        try:
            upload.save()
        except ValidationError as e:
            logger.error('Insertion failed: [error={}, message={}]'.format(e.__class__.__name__, e.messages))
            return handle_internal_error()

        upload.reload()
        logger.info('Bulk upload [pk={}, hash={}] inserted'.format(upload.id, upload.payload_hash))
    else:
        logger.info('Dry run: insertion into RegistrationBulkUpload not saved')

    registrations = parsing_output.get('registrations', [])
    if not registrations:
        logger.error('Missing registration rows')  # internal error
        return handle_internal_error()
    for reg_row in registrations:
        registration_row = BulkUploadedRegistration.create(
            reg_row.get('external_id', ''), upload, reg_row.get('csv_raw', ''), reg_row.get('csv_parsed', {})
        )
        logger.info('Inserting the registration row [external_id={}] '
                    'into the table BulkUploadedRegistration ...'.format(registration_row.external_id))
        if not dry_run:
            try:
                registration_row.save()
            except ValidationError as e:
                logger.error('Insertion failed: [error={}, message={}]'.format(e.__class__.__name__, e.messages))
                return handle_internal_error()
            upload.reload()
            logger.info('Registration row inserted: [pk={}, external_id={}, '
                        'upload_id={}]'.format(registration_row.id, registration_row.external_id, upload.id))
        else:
            logger.info('Dry run: insertion into BulkUploadedRegistration not saved')

    if not dry_run:
        logger.info('Database successfully populated for bulk upload: [upload_id={}, provider_id={}, schema_id={}, '
                    'initiator_id={}]'.format(upload.id, upload.provider._id, upload.schema._id, upload.initiator._id))
        upload.state = 'initialized'
        upload.save()
        return
    else:
        logger.info("Dry run: complete")
        return


def handle_internal_error():
    """Handle internal errors that are not caused by CSV template.
    0. Roll back
    1. Send an email to OSF Product team about the failure.
    2. Send an email to the upload initiator and ask them to try again only after they have heard back from us.
    """
    pass


def handle_external_error():
    """Handle external errors that are caused by CSV template.
    0. Roll back
    1. Send an email to OSF Product team about the failure.
    2. Send an email to the initiator and ask them to fix the CSV template.
    """
    pass
