import logging

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from framework import sentry
from framework.auth import Auth
from framework.celery_tasks import app as celery_app

from osf.exceptions import (
    RegistrationBulkCreationRowError,
    UserNotAffiliatedError,
    ValidationValueError,
    UserStateError,
)
from osf.models import (
    AbstractNode,
    Contributor,
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
        bulk_upload_row = RegistrationBulkUploadRow.create(
            upload,
            registration_row.get('csv_raw', ''),
            registration_row.get('csv_parsed'),
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

    # Check registration rows and pick up them one by one to create draft registrations
    registration_rows = RegistrationBulkUploadRow.objects.filter(upload__id=upload_id)
    initial_row_count = len(registration_rows)
    logger.info('Picked up [{}] registration rows for creation'.format(initial_row_count))

    draft_error_list = []  # a list that stores rows that have failed the draft creation
    approval_error_list = []  # a list that stores rows that have failed the approval process
    successful_row_count = 0
    for index, row in enumerate(registration_rows, 1):
        logger.info('Processing registration row [{}: upload={}, row={}]'.format(index, upload.id, row.id))
        row.is_picked_up = True
        if not dry_run:
            row.save()
        try:
            handle_registration_row(row, initiator, provider, schema, auto_approval=auto_approval, dry_run=dry_run)
            successful_row_count += 1
        except RegistrationBulkCreationRowError as e:
            logger.error(e.long_message)
            logger.error(e.error)
            sentry.log_exception()
            if auto_approval and e.approval_failure:
                approval_error_list.append(e.short_message)
            else:
                draft_error_list.append(e.short_message)
                if not dry_run:
                    if row.draft_registration:
                        row.draft_registration.delete()
                    elif e.draft_id:
                        DraftRegistration.objects.get(id=e.draft_id).delete()
                        row.delete()
                    else:
                        row.delete()
        except Exception as e:
            logger.error('Draft registration creation unexpected exception: [{}]'.format(repr(e)))
            sentry.log_exception()
            draft_error_list.append('Row: {}'.format(row.id))
            if not dry_run:
                if row.draft_registration:
                    row.draft_registration.delete()
                else:
                    row.delete()

    if len(draft_error_list) == initial_row_count:
        upload.state = JobState.DONE_ERROR
        message = 'All registration rows failed during bulk creation. ' \
                  'Upload ID: [{}], Draft Errors: [{}]'.format(upload_id, draft_error_list)
        sentry.log_message(message)
        logger.warning(message)
    elif len(draft_error_list) > 1 or len(approval_error_list) > 1:
        upload.state = JobState.DONE_PARTIAL
        message = 'Some registration rows failed during bulk creation. Upload ID: [{}]; Draft Errors: [{}]; ' \
                  'Approval Errors: [{}]'.format(upload_id, draft_error_list, approval_error_list)
        sentry.log_message(message)
        logger.error(message)
    else:
        upload.state = JobState.DONE_FULL
        logger.info('All registration rows succeeded for bulk creation. Upload ID: [{}].'.format(upload_id))
    if not dry_run:
        upload.save()
        logger.info('Sending emails to initiator/uploader ...')
        if upload.state == JobState.DONE_FULL:
            mails.send_mail(
                to_addr=initiator.username,
                mail=mails.REGISTRATION_BULK_UPLOAD_SUCCESS_ALL,
                fullname=initiator.fullname,
                auto_approval=auto_approval,
                count=initial_row_count,
                pending_submissions_url=get_provider_submission_url(provider),
            )
        elif upload.state == JobState.DONE_PARTIAL:
            mails.send_mail(
                to_addr=initiator.username,
                mail=mails.REGISTRATION_BULK_UPLOAD_SUCCESS_PARTIAL,
                fullname=initiator.fullname,
                auto_approval=auto_approval,
                total=initial_row_count,
                successes=successful_row_count,
                draft_errors=draft_error_list,
                failures=len(draft_error_list),
                pending_submissions_url=get_provider_submission_url(provider),
            )
        elif upload.state == JobState.DONE_ERROR:
            mails.send_mail(
                to_addr=initiator.username,
                mail=mails.REGISTRATION_BULK_UPLOAD_FAILURE_ALL,
                fullname=initiator.fullname,
                count=initial_row_count,
                draft_errors=draft_error_list,
            )
        else:
            message = 'Failed to send registration bulk upload outcome email due to invalid ' \
                      'upload state: [upload={}, state={}]'.format(upload.id, upload.state.name)
            logger.error(message)
            sentry.log_message(message)
        logger.info('Email sent to bulk upload initiator [{}]'.format(initiator._id))


def handle_registration_row(row, initiator, provider, schema, auto_approval=False, dry_run=True):
    """Create a draft registration for one registration row in a given bulk upload job.
    """

    metadata = row.csv_parsed.get('metadata', {})
    row_external_id = metadata.get('External ID', 'N/A')
    row_title = metadata.get('Title', 'N/A')
    responses = row.csv_parsed.get('registration_responses', {})
    auth = Auth(user=initiator)

    # Check node
    node = None
    node_id = metadata.get('Project GUID')
    if node_id:
        try:
            node = AbstractNode.objects.get(guids___id=node_id, is_deleted=False, type='osf.node')
        except AbstractNode.DoesNotExist:
            error = 'Node does not exist: [node_id={}]'.format(node_id)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        except AbstractNode.MultipleObjectsReturned:
            error = 'Multiple nodes returned: [node_id={}]'.format(node_id)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        try:
            initiator_contributor = node.contributor_set.get(user=initiator)
        except Contributor.DoesNotExist:
            error = 'Initiator [{}] must be a contributor on the project [{}]'.format(initiator._id, node._id)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        if initiator_contributor.permission not in [WRITE, ADMIN]:
            error = 'Initiator [{}] must at least have WRITE permission on the project [{}]'.format(initiator._id, node._id)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)

    # Prepare subjects
    subject_texts = metadata.get('Subjects', [])
    if not subject_texts:
        subject_texts = []
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
    if len(subject_ids) == 0:
        error = 'Missing subjects'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)

    # Prepare node licences
    parsed_license = metadata.get('License', {})
    if not parsed_license:
        parsed_license = {}
    license_name = parsed_license.get('name')
    require_fields = parsed_license.get('required_fields', {})
    if not require_fields:
        require_fields = {}
    year = require_fields.get('year')
    copyright_holders = require_fields.get('copyright_holders')
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
        'category': metadata.get('Category', ''),
        'description': metadata.get('Description', ''),
        'node_license': node_license,
    }

    # Prepare institutions
    affiliated_institutions = []
    institution_names = metadata.get('Affiliated Institutions', [])
    if not institution_names:
        institution_names = []
    for name in institution_names:
        try:
            institution = Institution.objects.get(name=name, is_deleted=False)
        except Institution.DoesNotExist:
            error = 'Institution not found: [name={}]'.format(name)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        affiliated_institutions.append(institution)

    # Prepare tags
    tags = metadata.get('Tags', [])

    # Prepare contributors
    admin_list = metadata.get('Admin Contributors', [])
    if not admin_list:
        admin_list = []
    if len(admin_list) == 0:
        error = 'Missing admin contributors'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
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
    if len(author_list) == 0:
        error = 'Missing bibliographic contributors'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)

    author_set = {contributor.get('email') for contributor in author_list}  # Bibliographic contributors
    contributor_list = admin_list + read_only_list + read_write_list
    contributor_set = set.union(admin_set, read_only_set, read_write_set)  # All contributors
    if not author_set.issubset(contributor_set):
        error = 'Bibliographic contributors must be one of admin, read-only or read-write'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)

    if dry_run:
        logger.info('Dry run: no draft registration will be created.')
        return

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
        # Remove all contributors except the initiator if created from an existing node
        if node:
            contributor_set = draft.contributor_set.all()
            for contributor in contributor_set:
                if initiator != contributor.user:
                    draft.remove_contributor(contributor, auth)
            draft.save()
        assert len(draft.contributor_set.all()) == 1, 'Draft should only have one contributor upon creation.'
        # Remove the initiator from the citation list
        # TODO: only remove the initiator form the citation list for certain providers
        initiator_contributor = draft.contributor_set.get(user=initiator)
        initiator_contributor.visible = False
        initiator_contributor.save()
        row.draft_registration = draft
        row.save()
    except Exception as e:
        # If the draft has been created already but failure happens before it is related to the registration row,
        # provide the draft id to the exception object for the caller to delete it after the exception is caught.
        draft_id = draft.id if draft else None
        raise RegistrationBulkCreationRowError(
            row.upload.id, row.id, row_title, row_external_id,
            draft_id=draft_id, error=repr(e),
        )

    # Set subjects
    # TODO: if available, capture specific exceptions during setting subject
    draft.set_subjects_from_relationships(subject_ids, auth)

    # Set affiliated institutions
    for institution in affiliated_institutions:
        try:
            draft.add_affiliated_institution(institution, initiator)
        except UserNotAffiliatedError:
            error = 'Initiator [{}] is not affiliated with institution [{}]'.format(initiator._id, institution._id)
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)

    # Set registration responses
    # TODO: if available, capture specific exceptions during setting responses
    draft.update_registration_responses(responses)

    # Set tags
    # TODO: if available, capture specific exceptions during setting tags
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
        except ValidationValueError as e:
            # `add_contributor_registered_or_not` throws several ValidationError / ValidationValueError that
            # needs to be treated differently.
            if e.message.endswith(' is already a contributor.'):
                logger.warning('Contributor already exists: [{}]'.format(email))
            else:
                error = 'This contributor cannot be added: [email="{}", error="{}"]'.format(email, e.message)
                raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
        except UserStateError as e:
            error = 'This contributor cannot be added: [email="{}", error="{}"]'.format(email, repr(e))
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
    draft.save()
    row.is_completed = True
    row.save()
    logger.info('Draft registration created: [{}]'.format(row.draft_registration.id))

    # Once draft registration has been created, bulk creation of this row is considered completed.
    # Any error that happens during auto approval doesn't affect the state of upload job and registration row.
    if auto_approval:
        logger.info('Provider [{}] has enabled auto approval.'.format(provider._id))
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


def get_provider_submission_url(provider):
    return f'{settings.DOMAIN}registries/{provider._id}/moderation/submissions/'
