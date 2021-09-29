import logging

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from framework import sentry
from framework.auth import Auth
from framework.celery_tasks import app as celery_app

from osf.exceptions import RegistrationBulkCreationRowError, UserNotAffiliatedError, ValidationValueError
from osf.models import (
    AbstractNode,
    DraftRegistration,
    Institution,
    OSFUser,
    RegistrationBulkUploadJob,
    RegistrationBulkUploadRow,
    RegistrationProvider,
    RegistrationSchema,
)
from osf.models.licenses import NodeLicense
from osf.models.registration_bulk_upload_job import JobState
from osf.utils.permissions import READ, WRITE, ADMIN

# from website import mails, settings

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
        bulk_upload_row = RegistrationBulkUploadRow(
            upload=upload, draft_registration=None, is_completed=False,
            is_picked_up=False, csv_raw=registration_row.get('csv_raw', ''),
            csv_parsed=registration_row.get('csv_parsed'),
        )
        bulk_upload_rows.append(bulk_upload_row)

    if dry_run:
        logger.info('Dry run: bulk insertion not run')
        logger.info('Dry run: complete')
        return

    try:
        logger.info('Bulk creating [{}] registration bulk upload rows ...'.format(len(bulk_upload_rows)))
        created_objects = RegistrationBulkUploadRow.objects.bulk_create(bulk_upload_rows)
    except (ValueError, IntegrityError) as e:
        upload.delete()
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


@celery_app.task(name='api.providers.tasks.monitor_registration_bulk_upload_jobs')
def monitor_registration_bulk_upload_jobs(dry_run=True):

    logger.info('Checking registration bulk upload jobs ...')
    bulk_uploads = RegistrationBulkUploadJob.objects.filter(state=JobState.INITIALIZED)
    logger.info('[{}] pending jobs found.'.format(len(bulk_uploads)))

    for upload in bulk_uploads:
        logger.info('Picked up job [upload={}, hash={}]'.format(upload.id, upload.payload_hash))
        upload.state = JobState.PICKED_UP
        bulk_create_registrations.delay(upload.id, dry_run=dry_run)
        if not dry_run:
            upload.save()
    if dry_run:
        logger.info('Dry run: bulk creation started in dry-run mode and job state was not updated')
    logger.info('[{}] jobs have been picked up and kicked off. This monitor task ends.'.format(len(bulk_uploads)))


@celery_app.task()
def bulk_create_registrations(upload_id, dry_run=True):

    try:
        upload = RegistrationBulkUploadJob.objects.get(id=upload_id)
    except RegistrationBulkUploadJob.DoesNotExist:
        # This error should not happen since this task is only called by `monitor_registration_bulk_upload_jobs`
        logger.error('Registration bulk upload job not found: [id={}] '.format(upload_id))
        sentry.log_exception()
        return

    # Retrieve bulk upload job
    provider = upload.provider
    auto_approval = upload.provider.bulk_upload_auto_approval
    schema = upload.schema
    initiator = upload.initiator
    logger.info(
        'Bulk creating draft registrations: [provider={}, schema={}, initiator={}, auto_approval={}]'.format(
            provider._id,
            schema._id,
            initiator._id,
            auto_approval,
        ),
    )

    # Check and pick up registration rows for creation
    registration_rows = RegistrationBulkUploadRow.objects.filter(upload__id=upload_id)
    initial_row_count = len(registration_rows)
    logger.info('Picked up [{}] registration rows for creation'.format(initial_row_count))

    draft_error_list = []
    approval_error_list = []
    for index, row in enumerate(registration_rows, 1):
        logger.info('Processing row [{}]'.format(index))
        row.is_picked_up = True
        if dry_run:
            continue
        row.save()
        try:
            handle_registration_row(row, initiator, provider, schema, auto_approval=auto_approval)
        except RegistrationBulkCreationRowError as e:
            logger.error(e.long_message)
            logger.error(e.error)
            sentry.log_exception()
            if e.approval_failure:
                approval_error_list.append(e.short_message)
            else:
                draft_error_list.append(e.short_message)
                if row.draft_registration:
                    row.draft_registration.delete()
                elif e.draft_id:
                    logger.error('draft id = [{}]'.format(e.draft_id))
                    DraftRegistration.objects.get(id=e.draft_id).delete()
                    row.delete()
                else:
                    row.delete()
    if len(draft_error_list) == initial_row_count:
        upload.state = JobState.DONE_ERROR
        sentry.log_message('All registration rows failed during bulk creation. '
                           'Upload ID: [{}], Draft Errors: [{}]'.format(upload_id, draft_error_list))
    elif len(draft_error_list) > 1 or len(approval_error_list) > 1:
        upload.state = JobState.DONE_PARTIAL
        sentry.log_message('Some registration rows failed during bulk creation. Upload ID: [{}]; Draft Errors: [{}]; '
                           'Approval Errors: [{}]'.format(upload_id, draft_error_list, approval_error_list))
    else:
        logger.info('All registration rows succeeded for bulk creation. Upload ID: [{}].'.format(upload_id))
        upload.state = JobState.DONE_FULL
    upload.save()
    # TODO: send emails with information form the two error list


def handle_registration_row(row, initiator, provider, schema, auto_approval=False):
    """Create a draft registration for one registration row in a given bulk upload job.
    """

    metadata = row.csv_parsed.get('metadata', {})
    row_external_id = metadata.get('External ID', 'N/A')
    row_title = metadata.get('Title', '')
    responses = row.csv_parsed.get('registration_responses', {})
    auth = Auth(user=initiator)

    # Check node
    node_id = metadata.get('Project GUID', '')
    node = None
    if node_id:
        try:
            node = AbstractNode.objects.get(guids___id=node_id, is_deleted=False, type='osf.node')
        except AbstractNode.DoesNotExist:
            error = 'Node does not exist: [node_id={}]'.format(node_id)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        except AbstractNode.MultipleObjectsReturned:
            error = 'Multiple nodes returned: [node_id={}]'.format(node_id)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)

    # Prepare subjects
    subject_texts = metadata.get('Subjects', [])
    subject_ids = []
    for text in subject_texts:
        subject_list = provider.all_subjects.filter(text=text)
        if not subject_list:
            error = 'Subject not found: [text={}]'.format(text)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        if len(subject_list) > 1:
            error = 'Duplicate subjects found: [text={}]'.format(text)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        subject_ids.append(subject_list.first()._id)

    # Prepare node licences
    license_name = metadata.get('License').get('name')
    year = metadata.get('License').get('required_fields', {}).get('year', None),
    copyright_holders = metadata.get('License').get('required_fields', {}).get('copyright_holders', None),
    try:
        node_license = NodeLicense.objects.get(name=license_name)
    except NodeLicense.DoesNotExist:
        error = 'License not found: [license_name={}]'.format(license_name)
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
    node_license = {
        'id': node_license.license_id,
    }
    if year and copyright_holders:
        node_license.update({
            'year': year,
            'copyright_holders': copyright_holders,
        })

    # Prepare editable fields
    data = {
        'title': row_title,
        'category': metadata.get('Category'),
        'description': metadata.get('Description'),
        'node_license': node_license,
    }

    # Prepare institutions
    affiliated_institutions = []
    institution_names = metadata.get('Affiliated Institutions', [])
    for name in institution_names:
        try:
            institution = Institution.objects.get(name=name, is_deleted=False)
        except Institution.DoesNotExist:
            error = 'Institution not found: [name={}]'.format(name)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        affiliated_institutions.append(institution)

    # Prepare tags
    tags = metadata.get('Tags')

    # Prepare contributors
    admin_list = metadata.get('Admin Contributors', [])
    if not admin_list:
        admin_list = []
    admin_set = {contributor.get('email') for contributor in admin_list}
    read_only_list = metadata.get('Read-Only Contributors', [])
    if not read_only_list:
        read_only_list = []
    read_only_set = {contributor.get('email') for contributor in read_only_list}
    read_write_list = metadata.get('Read-Write Contributors', [])
    if not read_write_list:
        read_write_list = []
    read_write_set = {contributor.get('email') for contributor in read_write_list}
    author_list = metadata.get('Bibliographic Contributors', [])
    if not author_list:
        author_list = []
    author_set = {contributor.get('email') for contributor in author_list}
    contributor_list = admin_list + read_only_list + read_write_list
    contributor_set = set.union(admin_set, read_only_set, read_write_set)

    if not author_set.issubset(contributor_set):
        error = 'Bibliographic contributors must be one of admin, read-only or read-write'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)

    # Creating the draft registration
    draft = None
    try:
        draft = DraftRegistration.create_from_node(
            initiator,
            schema,
            node=node,
            data=data,
            provider=provider,
        )
        # Remove the initiator from the citation list
        initiator_contributor = draft.contributor_set.get(user=initiator)
        initiator_contributor.visible = False
        initiator_contributor.save()
        row.draft_registration = draft
        row.save()
    except Exception as e:
        # If the has been created already but failure happens before it is related to the registration row,
        # provide the draft_id to the exception for deletion after the it is caught by the caller.
        draft_id = draft.id if draft else None
        raise RegistrationBulkCreationRowError(
            row.upload.id, row.id, row_title, row_external_id,
            draft_id=draft_id, error=repr(e),
        )

    # Set subjects
    draft.set_subjects_from_relationships(subject_ids, auth)

    # Set affiliated institutions
    for institution in affiliated_institutions:
        try:
            draft.add_affiliated_institution(institution, initiator)
        except UserNotAffiliatedError:
            error = 'Initiator [{}] is not affiliated with institution [{}]'.format(initiator._id, institution._id)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)

    # Set registration responses
    draft.update_registration_responses(responses)

    # Set tags
    draft.update_tags(tags, auth=auth)

    # Set contributors
    for contributor in contributor_list:
        email = contributor.get('email')
        full_name = contributor.get('full_name')
        if not email or not full_name:
            error = 'Invalid contributor format: missing email and/or full name'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        bibliographic = email in author_set
        permission = ADMIN if email in admin_set else (WRITE if email in read_write_set else READ)
        try:
            draft.add_contributor_registered_or_not(
                auth, full_name=full_name, email=email,
                permissions=permission, bibliographic=bibliographic,
            )
        except ValidationValueError:
            logger.warning('Contributor already exists: [{}]'.format(email))
            continue

    # Once draft registration has been created, bulk creation of this row is considered completed.
    # Any error that happens during approval doesn't affect the state of upload job and registration row.
    row.is_completed = True
    row.save()
    logger.info('Draft registration created: [{}]'.format(row.draft_registration.id))

    if auto_approval:
        draft = row.draft_registration
        try:
            draft.register(auth, save=True)
            registration = draft.registered_node
            registration.require_approval(initiator)
            registration.sanction.accept()
        except Exception as e:
            raise RegistrationBulkCreationRowError(
                row.upload.id, row.id, row_title, row_external_id,
                error=repr(e), approval_failure=True,
            )
        logger.info('Registration approved but pending moderation: [{}]'.format(registration.id))


def handle_error(initiator, inform_product=False, error_message=None):
    """Send emails information OSF product owner and/or registration admin about failures.
    """

    if error_message:
        logger.error(error_message)
        sentry.log_message(error_message)

    if inform_product:
        pass
    #     mails.send_mail(
    #         to_addr=settings.PRODUCT_OWNER_EMAIL_ADDRESS.get('Registration'),
    #         mail=mails.REGISTRATION_BULK_UPLOAD_PRODUCT_OWNER,
    #     )
    #
    if initiator:
        pass
    #     mails.send_mail(
    #         to_addr=initiator.username,
    #         mail=mails.REGISTRATION_BULK_UPLOAD_INITIATOR_FAILED_ON_HOLD,
    #         user=initiator,
    #         osf_support_email=settings.OSF_SUPPORT_EMAIL,
    #     )
