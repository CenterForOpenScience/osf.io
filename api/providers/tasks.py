import logging

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.utils import timezone

from framework import sentry
from framework.auth import Auth
from framework.celery_tasks import app as celery_app

from osf.exceptions import (
    NodeStateError,
    RegistrationBulkCreationContributorError,
    RegistrationBulkCreationRowError,
    UserNotAffiliatedError,
    UserStateError,
    ValidationValueError,
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
    Subject,
)
from osf.models.licenses import NodeLicense
from osf.models.registration_bulk_upload_job import JobState
from osf.models.registration_bulk_upload_row import RegistrationBulkUploadContributors
from osf.registrations.utils import get_registration_provider_submissions_url
from osf.utils.permissions import ADMIN

from website import mails, settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@celery_app.task()
def prepare_for_registration_bulk_creation(payload_hash, initiator_id, provider_id, parsing_output, dry_run=False):

    # Check initiator
    initiator = OSFUser.load(initiator_id)
    if not initiator:
        message = f'Bulk upload preparation failure: initiator [id={initiator_id}] not found'
        return handle_internal_error(initiator=None, provider=None, message=message, dry_run=dry_run)

    # Check provider
    try:
        provider = RegistrationProvider.objects.get(_id=provider_id)
    except RegistrationProvider.DoesNotExist:
        message = f'Bulk upload preparation failure: registration provider [_id={provider_id}] not found'
        return handle_internal_error(initiator=initiator, provider=None, message=message, dry_run=dry_run)
    except RegistrationProvider.MultipleObjectsReturned:
        message = f'Bulk upload preparation failure: multiple registration providers returned for [_id={provider_id}]'
        return handle_internal_error(initiator=initiator, provider=None, message=message, dry_run=dry_run)

    # Check parsing output
    if not parsing_output:
        message = 'Bulk upload preparation failure: missing parser output as task input'
        return handle_internal_error(initiator=initiator, provider=provider, message=message, dry_run=dry_run)

    # Check schema
    schema_id = parsing_output.get('schema_id', None)
    try:
        schema = RegistrationSchema.objects.get(_id=schema_id)
    except RegistrationSchema.DoesNotExist:
        message = f'Bulk upload preparation failure: registration schema [_id={schema_id}] not found'
        return handle_internal_error(initiator=initiator, provider=provider, message=message, dry_run=dry_run)
    except RegistrationSchema.MultipleObjectsReturned:
        message = f'Bulk upload preparation failure: multiple registration schemas [_id={schema_id}] returned'
        return handle_internal_error(initiator=initiator, provider=provider, message=message, dry_run=dry_run)

    # Create the bulk upload job
    upload = RegistrationBulkUploadJob.create(payload_hash, initiator, provider, schema)
    logger.info(f'Creating a registration bulk upload job with [hash={upload.payload_hash}] ...')
    if not dry_run:
        try:
            upload.save()
        except ValidationError as e:
            sentry.log_exception(e)
            message = 'Bulk upload preparation failure: failed to create the job'
            return handle_internal_error(initiator=initiator, provider=provider, message=message, dry_run=dry_run)
        upload.reload()
        logger.info(f'Bulk upload job created: [pk={upload.id}, hash={upload.payload_hash}]')
    else:
        logger.info('Dry run: insertion did not happen')

    # Create registration rows for the bulk upload job
    registration_rows = parsing_output.get('registrations', [])
    if not registration_rows:
        message = 'Bulk upload preparation failure: missing registration rows'
        return handle_internal_error(initiator=initiator, provider=provider, message=message, dry_run=dry_run)
    initial_row_count = len(registration_rows)
    logger.info(f'Preparing [{initial_row_count}] registration rows for bulk creation ...')

    bulk_upload_rows = set()
    draft_error_list = []
    try:
        for registration_row in registration_rows:
            bulk_upload_row = RegistrationBulkUploadRow.create(
                upload,
                registration_row.get('csv_raw', ''),
                registration_row.get('csv_parsed'),
            )
            metadata = bulk_upload_row.csv_parsed.get('metadata', {}) or {}
            row_external_id = metadata.get('External ID', 'N/A')
            row_title = metadata.get('Title', 'N/A')
            # Check duplicates with the database
            if RegistrationBulkUploadRow.objects.filter(row_hash=bulk_upload_row.row_hash).exists():
                error = 'Duplicate rows - existing row found in the system'
                exception = RegistrationBulkCreationRowError(upload.id, 'N/A', row_title, row_external_id, error=error)
                logger.error(exception.long_message)
                sentry.log_message(exception.long_message)
                draft_error_list.append(exception.short_message)
            else:
                # Don't `return` or `continue` so that duplicates within the rows can be detected
                pass
            # Check duplicates within the CSV
            if bulk_upload_row in bulk_upload_rows:
                error = 'Duplicate rows - CSV contains duplicate rows'
                exception = RegistrationBulkCreationRowError(upload.id, 'N/A', row_title, row_external_id, error=error)
                logger.error(exception.long_message)
                sentry.log_message(exception.long_message)
                draft_error_list.append(exception.short_message)
            else:
                bulk_upload_rows.add(bulk_upload_row)
    except Exception as e:
        upload.delete()
        return handle_internal_error(initiator=initiator, provider=provider, message=repr(e), dry_run=dry_run)

    # Cancel the preparation task if duplicates are found in the CSV and/or in DB
    if draft_error_list:
        upload.delete()
        mails.send_mail(
            to_addr=initiator.username,
            mail=mails.REGISTRATION_BULK_UPLOAD_FAILURE_DUPLICATES,
            fullname=initiator.fullname,
            count=initial_row_count,
            draft_errors=draft_error_list,
            osf_support_email=settings.OSF_SUPPORT_EMAIL,
        )
        return

    if dry_run:
        logger.info('Dry run: complete. Bulk creation did not run and emails are not sent.')
        return

    try:
        logger.info(f'Bulk creating [{len(bulk_upload_rows)}] registration rows ...')
        created_objects = RegistrationBulkUploadRow.objects.bulk_create(bulk_upload_rows)
    except (ValueError, IntegrityError) as e:
        upload.delete()
        sentry.log_exception(e)
        message = 'Bulk upload preparation failure: failed to create the rows.'
        return handle_internal_error(initiator=initiator, provider=provider, message=message, dry_run=dry_run)
    logger.info(f'[{len(created_objects)}] rows successfully prepared.')

    upload.state = JobState.INITIALIZED
    try:
        upload.save()
    except ValidationError as e:
        upload.delete()
        sentry.log_exception(e)
        message = 'Bulk upload preparation failure: job state update failed'
        return handle_internal_error(initiator=initiator, provider=provider, message=message, dry_run=dry_run)
    logger.info(
        f'Bulk upload preparation finished: [upload={upload.id}, state={upload.state.name}, '
        f'provider={upload.provider._id}, schema={upload.schema._id}, initiator={upload.initiator._id}]',
    )


@celery_app.task(name='api.providers.tasks.monitor_registration_bulk_upload_jobs')
def monitor_registration_bulk_upload_jobs(dry_run=True):

    bulk_uploads = RegistrationBulkUploadJob.objects.filter(state=JobState.INITIALIZED)
    number_of_jobs = len(bulk_uploads)
    logger.info(f'[{number_of_jobs}] pending registration bulk upload jobs found.')

    for upload in bulk_uploads:
        logger.info(f'Picking up job [upload={upload.id}, hash={upload.payload_hash}]')
        upload.state = JobState.PICKED_UP
        bulk_create_registrations.delay(upload.id, dry_run=dry_run)
        if not dry_run:
            upload.save()
    if dry_run:
        logger.info('Dry run: complete. Bulk creation started in dry-run mode and the job state was not updated')
    logger.info(f'Done. [{number_of_jobs}] jobs have been picked up and kicked off.')


@celery_app.task()
def bulk_create_registrations(upload_id, dry_run=True):

    try:
        upload = RegistrationBulkUploadJob.objects.get(id=upload_id)
    except RegistrationBulkUploadJob.DoesNotExist as e:
        # This error should not happen since this task is only called by `monitor_registration_bulk_upload_jobs`
        sentry.log_exception(e)
        message = f'Registration bulk upload job not found: [id={upload_id}]'
        return handle_internal_error(initiator=None, provider=None, message=message, dry_run=dry_run)

    # Retrieve bulk upload job
    provider = upload.provider
    auto_approval = upload.provider.bulk_upload_auto_approval
    schema = upload.schema
    initiator = upload.initiator
    logger.info(
        f'Bulk creating draft registrations: [provider={provider._id}, '
        f'schema={schema._id}, initiator={initiator._id}, auto_approval={auto_approval}]',
    )

    # Check registration rows and pick up them one by one to create draft registrations
    registration_rows = RegistrationBulkUploadRow.objects.filter(
        upload__id=upload_id,
        is_picked_up=False,
        is_completed=False,
    )
    initial_row_count = len(registration_rows)
    logger.info(f'Picked up [{initial_row_count}] registration rows for creation')

    draft_error_list = []  # a list that stores rows that have failed the draft creation
    approval_error_list = []  # a list that stores rows that have failed the approval process
    successful_row_count = 0
    for index, row in enumerate(registration_rows, 1):
        logger.info(f'Processing registration row [{index}: upload={upload.id}, row={row.id}]')
        row.is_picked_up = True
        if not dry_run:
            row.save()
        try:
            handle_registration_row(row, initiator, provider, schema, auto_approval=auto_approval, dry_run=dry_run)
            successful_row_count += 1
        except RegistrationBulkCreationRowError as e:
            logger.error(e.long_message)
            logger.error(e.error)
            sentry.log_exception(e)
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
            error = f'Bulk upload registration creation encountered ' \
                    f'an unexpected exception: [row="{row.id}", error="{repr(e)}"]'
            logger.error(error)
            sentry.log_message(error)
            sentry.log_exception(e)
            draft_error_list.append(f'Title: N/A, External ID: N/A, Row Hash: {row.row_hash}, Error: Unexpected')
            if not dry_run:
                if row.draft_registration:
                    row.draft_registration.delete()
                else:
                    row.delete()
    bulk_upload_finish_job(
        upload,
        initial_row_count,
        successful_row_count,
        draft_error_list,
        approval_error_list,
        dry_run=dry_run,
    )


def handle_registration_row(row, initiator, provider, schema, auto_approval=False, dry_run=True):
    """Create a draft registration for one registration row in a given bulk upload job.
    """

    metadata = row.csv_parsed.get('metadata', {}) or {}
    row_external_id = metadata.get('External ID', 'N/A')
    row_title = metadata.get('Title', 'N/A')
    responses = row.csv_parsed.get('registration_responses', {}) or {}
    auth = Auth(user=initiator)

    # Check node
    node_id = metadata.get('Project GUID')
    node = check_node(node_id, initiator, row, row_title, row_external_id)
    # Prepare tags
    tags = metadata.get('Tags', [])
    # Prepare subjects
    subject_texts = metadata.get('Subjects', []) or []
    subject_ids = prepare_subjects(subject_texts, provider, row, row_title, row_external_id)
    # Prepare institutions
    institution_names = metadata.get('Affiliated Institutions', []) or []
    affiliated_institutions = prepare_institutions(institution_names, initiator, row, row_title, row_external_id)
    # Prepare contributors
    admin_list = metadata.get('Admin Contributors', []) or []
    read_only_list = metadata.get('Read-Only Contributors', []) or []
    read_write_list = metadata.get('Read-Write Contributors', []) or []
    author_list = metadata.get('Bibliographic Contributors', []) or []
    parsed_contributors = prepare_contributors(
        admin_list,
        read_only_list,
        read_write_list,
        author_list,
        row,
        row_title,
        row_external_id,
    )
    # Prepare node licences
    parsed_license = metadata.get('License', {}) or {}
    node_license = prepare_license(parsed_license, row, row_title, row_external_id)
    # Prepare editable fields
    data = {
        'title': row_title,
        'category': metadata.get('Category', ''),
        'description': metadata.get('Description', ''),
        'node_license': node_license,
    }
    # Return if dry-run is enabled
    if dry_run:
        logger.info('Dry run: complete. No draft registration will be created.')
        return

    # Creating the draft registration
    draft = bulk_upload_create_draft_registration(auth, initiator, schema, node, data, provider, row, row_title, row_external_id)
    # Set tags, subjects and registration responses
    try:
        draft.update_tags(tags, auth=auth)
        draft.set_subjects_from_relationships(subject_ids, auth)
        draft.update_registration_responses(responses)
    except Exception as e:
        error = f'Fail to update registration: {repr(e)}'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, row_title, row_external_id, error=error)
    # Set contributors
    set_draft_contributors(draft, auth, parsed_contributors, row, row_title, row_external_id)
    # Set affiliated institutions
    set_affiliated_institutions(initiator, draft, affiliated_institutions, row, row_title, row_external_id)
    # Save draft and update row state
    draft.save()
    row.is_completed = True
    row.save()
    logger.info(
        f'Draft registration created: [guid={row.draft_registration._id}] '
        f'for registration row [hash={row.row_hash}] in upload job [pk={row.upload.id}]',
    )
    # Register the draft
    bulk_upload_register_draft(
        initiator,
        provider,
        row,
        row_title,
        row_external_id,
        auth=auth,
        auto_approval=auto_approval,
    )
    return


def check_node(node_id, initiator, row, title, external_id):
    """Check if a node exists for the given `node_id`. If so, return the node object; otherwise return `None`.
    """
    node = None
    if node_id:
        try:
            node = AbstractNode.objects.get(guids___id=node_id, is_deleted=False, type='osf.node')
        except AbstractNode.DoesNotExist:
            error = f'Node does not exist: [node_id={node_id}]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        except AbstractNode.MultipleObjectsReturned:
            error = f'Multiple nodes returned: [node_id={node_id}]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        try:
            initiator_contributor = node.contributor_set.get(user=initiator)
        except Contributor.DoesNotExist:
            error = f'Initiator [{initiator._id}] must be a contributor on the project [{node._id}]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        if initiator_contributor.permission != ADMIN:
            error = f'Initiator [{initiator._id}] must have admin permission on the project [{node._id}]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
    return node


def prepare_subjects(subject_texts, provider, row, title, external_id):
    """Prepare the subjects that are used for registration creation. Return a list of subject ID.
    """
    if not subject_texts:
        error = 'Missing subjects'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
    subject_ids = []
    for text in subject_texts:
        try:
            subject = provider.all_subjects.get(text=text)
        except Subject.DoesNotExist:
            error = f'Subject not found: [text={text}]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        except Subject.MultipleObjectsReturned:
            error = f'Duplicate subjects found: [text={text}]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        subject_ids.append(subject._id)
    return subject_ids


def prepare_license(parsed_license, row, title, external_id):
    """Prepare the license that are used for registration creation. Return a `NodeLicense` object.
    """
    license_name = parsed_license.get('name')
    require_fields = parsed_license.get('required_fields', {}) or {}
    year = require_fields.get('year')
    copyright_holders = require_fields.get('copyright_holders')
    try:
        node_license = NodeLicense.objects.get(name=license_name)
    except NodeLicense.DoesNotExist:
        error = f'License not found: [license_name={license_name}]'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
    node_license = {
        'id': node_license.license_id,
    }
    if year and copyright_holders:
        node_license.update({
            'year': year,
            'copyright_holders': copyright_holders,
        })
    return node_license


def prepare_institutions(institution_names, initiator, row, title, external_id):
    """Prepare affiliated institutions that are used for registration creation. Return a list of `Institution` objects.
    """
    affiliated_institutions = []
    for name in institution_names:
        try:
            institution = Institution.objects.get(name=name, is_deleted=False)
        except Institution.DoesNotExist:
            error = f'Institution not found: [name={name}]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        if not initiator.is_affiliated_with_institution(institution):
            error = f'Initiator [{initiator._id}] is not affiliated with institution [{institution._id}]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        affiliated_institutions.append(institution)
    return affiliated_institutions


def set_affiliated_institutions(initiator, draft, affiliated_institutions, row, title, external_id):
    """Set institution affiliations for a given draft.
    """
    for institution in affiliated_institutions:
        try:
            draft.add_affiliated_institution(institution, initiator)
        except UserNotAffiliatedError:
            error = f'Initiator [{initiator._id}] is not affiliated with institution [{institution._id}]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)


def prepare_contributors(admin_list, read_only_list, read_write_list, author_list, row, title, external_id):
    """Prepare contributors for registration creation. Return a `RegistrationBulkUploadContributors` object.
    """
    if not admin_list:
        error = 'Missing admin contributors'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
    admin_set = {contributor.get('email') for contributor in admin_list}
    read_write_set = {contributor.get('email') for contributor in read_write_list}
    read_only_set = {contributor.get('email') for contributor in read_only_list}
    if not author_list:
        error = 'Missing bibliographic contributors'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)

    author_set = {contributor.get('email') for contributor in author_list}  # Bibliographic contributors
    contributor_list = admin_list + read_only_list + read_write_list
    contributor_set = set.union(admin_set, read_only_set, read_write_set)  # All contributors
    if not author_set.issubset(contributor_set):
        error = 'Bibliographic contributors must be one of admin, read-only or read-write'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
    return RegistrationBulkUploadContributors(admin_set, read_only_set, read_write_set, author_set, contributor_list)


def set_draft_contributors(draft, auth, parsed_contributors, row, title, external_id):
    """Set contributors, their permissions and citation info for a given draft.
    """
    for contributor in parsed_contributors.contributor_list:
        email = contributor.get('email')
        full_name = contributor.get('full_name')
        if not email or not full_name:
            error = 'Invalid contributor format: missing email and/or full name'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        bibliographic = parsed_contributors.is_bibliographic(email)
        try:
            permission = parsed_contributors.get_permission(email)
        except RegistrationBulkCreationContributorError as e:
            error = f'This contributor cannot be added: [email="{email}", error="{repr(e)}"]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        try:
            draft.add_contributor_registered_or_not(
                auth, full_name=full_name, email=email,
                permissions=permission, bibliographic=bibliographic,
            )
        except ValidationValueError as e:
            # `add_contributor_registered_or_not` throws several ValidationError / ValidationValueError that
            # needs to be treated differently.
            if e.message.endswith(' is already a contributor.'):
                logger.warning(f'Contributor already exists: [{email}]')
            else:
                error = f'This contributor cannot be added: [email="{email}", error="{e.message}"]'
                raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
        except UserStateError as e:
            error = f'This contributor cannot be added: [email="{email}", error="{repr(e)}"]'
            raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)


def bulk_upload_create_draft_registration(auth, initiator, schema, node, data, provider, row, title, external_id):
    """Create a draft registration from one registration row.
    """
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
            # Temporarily make initiator contributor visible so that removal of the others can succeed.
            initiator_contributor = draft.contributor_set.get(user=initiator)
            if not initiator_contributor.visible:
                initiator_contributor.visible = True
                initiator_contributor.save()
            contributor_set = draft.contributor_set.all()
            for contributor in contributor_set:
                if initiator != contributor.user:
                    is_removed = draft.remove_contributor(contributor, auth)
                    assert is_removed, 'Removal of an non-initiator contributor from the draft has failed'
            draft.save()
        assert len(draft.contributor_set.all()) == 1, 'Draft should only have one contributor upon creation.'
        # Remove the initiator from the citation list
        initiator_contributor = draft.contributor_set.get(user=initiator)
        initiator_contributor.visible = False
        initiator_contributor.save()
        # Relate the draft to the row
        row.draft_registration = draft
        row.save()
    except Exception as e:
        # If the draft has been created already but failure happens before it is related to the registration row,
        # provide the draft id to the exception object for the caller to delete it after the exception is caught.
        draft_id = draft.id if draft else None
        raise RegistrationBulkCreationRowError(
            row.upload.id,
            row.id,
            title,
            external_id,
            draft_id=draft_id,
            error=repr(e),
        )
    return draft


def bulk_upload_register_draft(initiator, provider, row, title, external_id, auth=None, auto_approval=False):
    """Register the draft and require approval. If `auto_approval` is `True`, then it is "contributor-admin-approved".
    """
    # Get/set auth
    if not auth:
        auth = Auth(user=initiator)
    # Register draft
    try:
        registration = row.draft_registration.register(auth, save=True)
    except NodeStateError as e:
        error = f'Fail to register draft: {repr(e)}'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
    except Exception as e:
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=repr(e))
    logger.info(f'Registration [{registration._id}] created from draft [{row.draft_registration._id}]')
    # Requires approval
    try:
        registration.require_approval(initiator)
    except NodeStateError as e:
        error = f'Fail to require approval: {repr(e)}'
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=error)
    except Exception as e:
        raise RegistrationBulkCreationRowError(row.upload.id, row.id, title, external_id, error=repr(e))
    logger.info(f'Approval required for registration [{registration._id}]')
    # Once draft registration and registrations have been created, bulk creation of this row is considered completed.
    # Any error that happens during `registration.sanction.accept()` doesn't affect the state of upload job and the
    # registration row.
    if auto_approval:
        try:
            registration.sanction.accept()
        except Exception as e:
            raise RegistrationBulkCreationRowError(
                row.upload.id, row.id, title, external_id,
                error=repr(e), approval_failure=True,
            )
        logger.info(
            f'Provider [{provider._id}] has enabled auto-approval; '
            f'thus registration [{registration._id}] has been approved but pending moderation',
        )
    return registration


def bulk_upload_finish_job(upload, row_count, success_count, draft_errors, approval_errors, dry_run=True):
    """Finish the bulk upload job: handle errors (if any), send outcome emails, and update job state.
    """
    provider = upload.provider
    auto_approval = upload.provider.bulk_upload_auto_approval
    initiator = upload.initiator

    # All registration rows have failed draft creation
    if len(draft_errors) == row_count:
        upload.state = JobState.DONE_ERROR
        message = f'All registration rows failed during bulk creation. ' \
                  f'Upload ID: [{upload.id}], Draft Errors: [{draft_errors}]'
        sentry.log_message(message)
        logger.error(message)
    # Some registration rows have failed draft creation
    elif draft_errors:
        upload.state = JobState.DONE_PARTIAL
        if not approval_errors:
            message = f'Some registration rows failed during bulk creation. ' \
                      f'Upload ID: [{upload.id}]; Draft Errors: [{draft_errors}].'
        else:
            message = f'Some registration rows failed during bulk creation and some failed to be approved. ' \
                      f'Upload ID: [{upload.id}]; Draft Errors: [{draft_errors}]; Approval Errors: [{approval_errors}]'
        sentry.log_message(message)
        logger.warning(message)
    # All registration rows have finish the draft creation
    else:
        upload.state = JobState.DONE_FULL
        if not approval_errors:
            logger.info(f'All registration rows succeeded for bulk creation. Upload ID: [{upload.id}].')
        else:
            message = f'All registration rows succeeded for bulk creation but some have failed to be approved.' \
                      f' Upload ID: [{upload.id}]; Approval Errors: [{approval_errors}]'
            sentry.log_message(message)
            logger.warning(message)
    # Use `.sort()` to stabilize the order
    draft_errors.sort()
    approval_errors.sort()
    if not dry_run:
        upload.save()
        if upload.state == JobState.DONE_FULL:
            mails.send_mail(
                to_addr=initiator.username,
                mail=mails.REGISTRATION_BULK_UPLOAD_SUCCESS_ALL,
                fullname=initiator.fullname,
                auto_approval=auto_approval,
                count=row_count,
                pending_submissions_url=get_registration_provider_submissions_url(provider),
            )
        elif upload.state == JobState.DONE_PARTIAL:
            mails.send_mail(
                to_addr=initiator.username,
                mail=mails.REGISTRATION_BULK_UPLOAD_SUCCESS_PARTIAL,
                fullname=initiator.fullname,
                auto_approval=auto_approval,
                total=row_count,
                successes=success_count,
                draft_errors=draft_errors,
                approval_errors=approval_errors,
                failures=len(draft_errors),
                pending_submissions_url=get_registration_provider_submissions_url(provider),
                osf_support_email=settings.OSF_SUPPORT_EMAIL,
            )
        elif upload.state == JobState.DONE_ERROR:
            mails.send_mail(
                to_addr=initiator.username,
                mail=mails.REGISTRATION_BULK_UPLOAD_FAILURE_ALL,
                fullname=initiator.fullname,
                count=row_count,
                draft_errors=draft_errors,
                osf_support_email=settings.OSF_SUPPORT_EMAIL,
            )
        else:
            message = f'Failed to send registration bulk upload outcome email due to invalid ' \
                      f'upload state: [upload={upload.id}, state={upload.state.name}]'
            logger.error(message)
            sentry.log_message(message)
            return
        upload.email_sent = timezone.now()
        upload.save()
        logger.info(f'Email sent to bulk upload initiator [{initiator._id}]')


def handle_internal_error(initiator=None, provider=None, message=None, dry_run=True):
    """Log errors that happened due to unexpected bug and send emails the uploader (if available)
    about failures. Product owner (if available) is informed as well with more details. Emails are
    not sent during dry run.
    """

    if not message:
        message = 'Registration bulk upload failure'
    logger.error(message)
    sentry.log_message(message)

    if not dry_run:
        if initiator:
            mails.send_mail(
                to_addr=initiator.username,
                mail=mails.REGISTRATION_BULK_UPLOAD_UNEXPECTED_FAILURE,
                fullname=initiator.fullname,
                osf_support_email=settings.OSF_SUPPORT_EMAIL,
            )
        inform_product_of_errors(initiator=initiator, provider=provider, message=message)


def inform_product_of_errors(initiator=None, provider=None, message=None):
    """Inform product owner of internal errors.
    """

    email = settings.PRODUCT_OWNER_EMAIL_ADDRESS.get('Registration')
    if not email:
        logger.warning('Missing email for OSF Registration product owner.')
        return

    if not message:
        message = 'Bulk upload preparation failure'
    user = f'{initiator._id}, {initiator.fullname}, {initiator.username}' if initiator else 'UNIDENTIFIED'
    provider_name = provider.name if provider else 'UNIDENTIFIED'
    mails.send_mail(
        to_addr=email,
        mail=mails.REGISTRATION_BULK_UPLOAD_PRODUCT_OWNER,
        message=message,
        user=user,
        provider_name=provider_name,
    )
