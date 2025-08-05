"""
Force-archive "stuck" registrations (i.e. failed to completely archive).
USE WITH CARE.

Usage:

    # Check if Registration abc12 and qwe34 are stuck
    python3 manage.py force_archive --check --guids abc12 qwe34

    # Dry-run a force-archive of abc12 and qwe34. Verifies that the force-archive can occur.
    python3 manage.py force_archive --dry --guids abc12 qwe34

    # Force-archive abc12 and qwe34
    python3 manage.py force_archive --guids abc12 qwe34

    # Force archive OSFS and Dropbox on abc12
    python3 manage.py force_archive --addons dropbox --guids abc12
"""

from copy import deepcopy
from rest_framework import status as http_status
import json
import logging
import requests
import contextlib

import django
django.setup()
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db.utils import IntegrityError
from django.utils import timezone

from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder, OsfStorageFileNode
from framework import sentry
from framework.exceptions import HTTPError
from osf.models import AbstractNode, Node, NodeLog, Registration, BaseFileNode
from osf.models.files import TrashedFileNode
from osf.exceptions import RegistrationStuckRecoverableException, RegistrationStuckBrokenException
from api.base.utils import waterbutler_api_url_for
from scripts import utils as script_utils
from website.archiver import ARCHIVER_SUCCESS
from website.settings import ARCHIVE_TIMEOUT_TIMEDELTA, ARCHIVE_PROVIDER, COOKIE_NAME
from website.files.utils import attach_versions

logger = logging.getLogger(__name__)

# Logging globals
CHECKED_OKAY = []
CHECKED_STUCK_RECOVERABLE = []
CHECKED_STUCK_BROKEN = []
VERIFIED = []
ARCHIVED = []
SKIPPED = []

# Ignorable NodeLogs
LOG_WHITELIST = (
    'affiliated_institution_added',
    'category_updated',
    'comment_added',
    'comment_removed',
    'comment_restored',
    'comment_updated',
    'confirm_ham',
    'confirm_spam',
    'contributor_added',
    'contributor_removed',
    'contributors_reordered',
    'edit_description',
    'edit_title',
    'embargo_approved',
    'embargo_cancelled',
    'embargo_completed',
    'embargo_initiated',
    'embargo_terminated',
    'external_ids_added',
    'file_tag_added',
    'flag_spam',
    'guid_metadata_updated',
    'license_changed',
    'made_contributor_invisible',
    'made_private',
    'made_public',
    'made_wiki_private',
    'made_wiki_public',
    'node_removed',
    'node_access_requests_disabled',
    'node_access_requests_enabled',
    'permissions_updated',
    'pointer_created',
    'pointer_removed',
    'prereg_registration_initiated',
    'project_created',
    'project_deleted',
    'project_registered',
    'registration_approved',
    'registration_cancelled',
    'registration_initiated',
    'retraction_approved',
    'retraction_initiated',
    'subjects_updated',
    'tag_added',
    'tag_removed',
    'wiki_deleted',
    'wiki_updated',
    'node_access_requests_disabled',
    'view_only_link_added',
    'view_only_link_removed',
)

# Require action, but recoverable from
LOG_GREYLIST = (
    'addon_file_moved',
    'addon_file_renamed',
    'osf_storage_file_added',
    'osf_storage_file_removed',
    'osf_storage_file_updated',
    'osf_storage_folder_created'
)
VERIFY_PROVIDER = (
    'addon_file_moved',
    'addon_file_renamed'
)

# Permissible in certain circumstances after communication with user
PERMISSIBLE_BLACKLIST = (
    'dropbox_folder_selected',
    'dropbox_node_authorized',
    'dropbox_node_deauthorized',
    'addon_removed',
    'addon_added'
)

DEFAULT_PERMISSIBLE_ADDONS = (
    'osfstorage',
)

def complete_archive_target(reg, addon_short_name):
    # Cache registration files count
    reg.update_files_count()

    archive_job = reg.archive_job
    target = archive_job.get_target(addon_short_name)
    target.status = ARCHIVER_SUCCESS
    target.save()
    archive_job._post_update_target()

def perform_wb_copy(reg, node_settings, delete_collisions=False, skip_collisions=False):
    src, dst, user = reg.archive_job.info()
    if dst.files.filter(name=node_settings.archive_folder_name.replace('/', '-')).exists():
        if not delete_collisions and not skip_collisions:
            raise Exception('Archive folder for {} already exists. Investigate manually and rerun with either --delete-collisions or --skip-collisions')
        if delete_collisions:
            archive_folder = dst.files.exclude(type='osf.trashedfolder').get(name=node_settings.archive_folder_name.replace('/', '-'))
            logger.info(f'Removing {archive_folder}')
            archive_folder.delete()
        if skip_collisions:
            complete_archive_target(reg, node_settings.short_name)
            return
    cookie = user.get_or_create_cookie().decode()
    params = {'cookie': cookie}
    data = {
        'action': 'copy',
        'path': '/',
        'rename': node_settings.archive_folder_name.replace('/', '-'),
        'resource': dst._id,
        'provider': ARCHIVE_PROVIDER,
    }
    url = waterbutler_api_url_for(src._id, node_settings.short_name, _internal=True, base_url=src.osfstorage_region.waterbutler_url, **params)
    res = requests.post(url, data=json.dumps(data), cookies={COOKIE_NAME: cookie})
    if res.status_code not in (http_status.HTTP_200_OK, http_status.HTTP_201_CREATED, http_status.HTTP_202_ACCEPTED):
        http_exception = HTTPError(res.status_code)
        sentry.log_exception(http_exception)
        raise http_exception

def manually_archive(tree, reg, node_settings, parent=None):
    if not isinstance(tree, list):
        tree = [tree]
    for filenode in tree:
        if filenode['deleted']:
            continue
        if filenode.get('parent') and (
                (parent is not None and filenode['parent']._id != parent.copied_from._id)
                or (parent is None and filenode['parent'].name != '')):
            # Not the parent we're looking for
            continue
        file_obj = filenode['object']
        cloned = file_obj.clone()
        if cloned.is_deleted:
            if cloned.is_file:
                cloned.recast(OsfStorageFile._typedmodels_type)
            else:
                cloned.recast(OsfStorageFolder._typedmodels_type)
        if not parent:
            parent = reg.get_addon('osfstorage').get_root()
            cloned.name = node_settings.archive_folder_name
        else:
            cloned.name = filenode['name']
        cloned.parent = parent
        cloned.target = reg
        cloned.copied_from = file_obj
        try:
            cloned.save()
        except IntegrityError:
            # Files sometimes already created
            cloned = reg.files.get(name=cloned.name)

        if file_obj.versions.exists() and filenode['version']:  # Min version identifier is 1
            if not cloned.versions.filter(identifier=filenode['version']).exists():
                attach_versions(cloned, file_obj.versions.filter(identifier__lte=filenode['version']), file_obj)

        if filenode.get('children'):
            manually_archive(filenode['children'], reg, node_settings, parent=cloned)


def modify_file_tree_recursive(reg_id, tree, file_obj, deleted=None, cached=False, rename=None, revert=False, move_under=None):
    # Note: `deleted` has three possible states:
    # - True: indicates file should be marked as deleted
    # - False: indicates file should be added or undeleted
    # - None: indicates no change to deletion status, allows renames/reverts
    retree = []
    noop = True
    target_parent = move_under or file_obj.parent
    if not isinstance(tree, list):
        tree = [tree]
    for filenode in tree:
        if (file_obj.is_deleted or file_obj.target._id != reg_id) and not cached and filenode['object'].id == target_parent.id:
            filenode['children'].append({
                'deleted': None,
                'object': file_obj,
                'name': file_obj.name,
                'version': int(file_obj.versions.latest('created').identifier) if file_obj.versions.exists() else None
            })
            cached = True
            if move_under:
                noop = False
        if filenode['object']._id == file_obj._id:
            if deleted is not None:
                filenode['deleted'] = deleted
                noop = False
            elif deleted is None:
                if revert:
                    if not isinstance(filenode['version'], int):
                        raise Exception('Unexpected type for version: got {}'.format(type(filenode['version'])))
                    filenode['version'] = filenode['version'] - 1
                    noop = False
                elif rename and rename != filenode['name']:
                    filenode['name'] = rename
                    noop = False
                elif move_under:
                    filenode['parent'] = move_under
                    noop = False
        if move_under and move_under._id == filenode['object']._id:
            for child in filenode['children']:
                if child['object']._id == file_obj._id:
                    child['parent'] = move_under
                    break
            else:
                filenode['children'].append({
                    'parent': move_under,
                    'object': file_obj,
                    'name': file_obj.name,
                    'deleted': file_obj.is_deleted,
                    'version': int(file_obj.versions.latest('created').identifier) if file_obj.versions.exists() else None
                })
            noop = False
        if filenode.get('children'):
            filenode['children'], _noop = modify_file_tree_recursive(reg_id, filenode['children'], file_obj, deleted, cached, rename, revert, move_under)
            if noop:
                noop = _noop
        retree.append(filenode)
    return retree, noop

def get_logs_to_revert(reg):
    return NodeLog.objects.filter(
        Q(node__id__in=Node.objects.get_children(reg.registered_from).values_list('id', flat=True)) | Q(node__id=reg.registered_from.id))\
        .filter(date__gte=reg.registered_date).exclude(action__in=LOG_WHITELIST)\
        .filter(
            Q(node=reg.registered_from) |
            (Q(params__source__nid=reg.registered_from._id) | Q(params__destination__nid=reg.registered_from._id))).order_by('-date')

def get_file_obj_from_log(log, reg):
    try:
        return BaseFileNode.objects.get(_id=log.params['urls']['view'].split('/')[4])
    except KeyError:
        path = log.params.get('path', '').split('/')
        if log.action in ['addon_file_moved', 'addon_file_renamed']:
            try:
                return BaseFileNode.objects.get(_id=log.params['source']['path'].rstrip('/').split('/')[-1])
            except (KeyError, BaseFileNode.DoesNotExist):
                return BaseFileNode.objects.get(_id=log.params['destination']['path'].rstrip('/').split('/')[-1])
        elif log.action == 'osf_storage_file_removed':
            candidates = BaseFileNode.objects.filter(
                target_object_id=reg.registered_from.id,
                target_content_type_id=ContentType.objects.get_for_model(AbstractNode).id,
                name=path[-1] or path[-2],
                deleted_on__lte=log.date
            ).order_by('-deleted_on')
        else:
            # Generic fallback
            candidates = BaseFileNode.objects.filter(
                target_object_id=reg.registered_from.id,
                target_content_type_id=ContentType.objects.get_for_model(AbstractNode).id,
                name=path[-1] or path[-2],
                created__lte=log.date
            ).order_by('-created')

        if candidates.exists():
            return candidates.first()

        raise BaseFileNode.DoesNotExist(f"No file found for name '{path[-1] or path[-2]}' before {log.date}")


def handle_file_operation(file_tree, reg, file_obj, log, obj_cache):
    logger.info(f'Reverting {log.action} {file_obj._id}:{file_obj.name} from {log.date}')

    if log.action in ['osf_storage_file_added', 'osf_storage_folder_created']:
        return modify_file_tree_recursive(reg._id, file_tree, file_obj, deleted=True, cached=bool(file_obj._id in obj_cache))
    elif log.action == 'osf_storage_file_removed':
        return modify_file_tree_recursive(reg._id, file_tree, file_obj, deleted=False, cached=bool(file_obj._id in obj_cache))
    elif log.action == 'osf_storage_file_updated':
        return modify_file_tree_recursive(reg._id, file_tree, file_obj, cached=bool(file_obj._id in obj_cache), revert=True)
    elif log.action == 'addon_file_moved':
        parent = BaseFileNode.objects.get(_id__in=obj_cache, name='/{}'.format(log.params['source']['materialized']).rstrip('/').split('/')[-2])
        return modify_file_tree_recursive(reg._id, file_tree, file_obj, cached=bool(file_obj._id in obj_cache), move_under=parent)
    elif log.action == 'addon_file_renamed':
        return modify_file_tree_recursive(reg._id, file_tree, file_obj, cached=bool(file_obj._id in obj_cache), rename=log.params['source']['name'])
    else:
        raise ValueError(f'Unexpected log action: {log.action}')

def revert_log_actions(file_tree, reg, obj_cache, permissible_addons):
    logs_to_revert = get_logs_to_revert(reg)

    if len(permissible_addons) > 1:
        logs_to_revert = logs_to_revert.exclude(action__in=PERMISSIBLE_BLACKLIST)

    for log in list(logs_to_revert):
        file_obj = get_file_obj_from_log(log, reg)
        assert file_obj.target in reg.registered_from.root.node_and_primary_descendants()

        file_tree, noop = handle_file_operation(file_tree, reg, file_obj, log, obj_cache)
        assert not noop, f'{reg._id}: Failed to revert action for NodeLog {log._id}'

        if file_obj._id not in obj_cache:
            obj_cache.add(file_obj._id)

    return file_tree

def build_file_tree(reg, node_settings, *args, **kwargs):
    n = reg.registered_from
    obj_cache = set(n.files.values_list('_id', flat=True))

    def _recurse(file_obj, node):
        ct_id = ContentType.objects.get_for_model(node.__class__()).id
        serialized = {
            'object': file_obj,
            'name': file_obj.name,
            'deleted': file_obj.is_deleted,
            'version': int(file_obj.versions.latest('created').identifier) if file_obj.versions.exists() else None
        }
        if not file_obj.is_file:
            nonlocal reg
            all_children = OsfStorageFileNode.objects.filter(
                target_object_id=node.id,
                target_content_type_id=ct_id,
                parent_id=file_obj.id
            ).union(
                TrashedFileNode.objects.filter(
                    target_object_id=node.id,
                    target_content_type_id=ct_id,
                    parent_id=file_obj.id,
                    modified__gt=reg.archive_job.created,
                )
            )
            serialized['children'] = [_recurse(child, node) for child in all_children]
        return serialized

    current_tree = _recurse(node_settings.get_root(), n)
    return revert_log_actions(current_tree, reg, obj_cache, *args, **kwargs)

def archive(registration, *args, permissible_addons=DEFAULT_PERMISSIBLE_ADDONS, allow_unconfigured=False, **kwargs):
    for reg in registration.node_and_primary_descendants():
        reg.registered_from.creator.get_or_create_cookie()  # Allow WB requests
        if reg.archive_job.status == ARCHIVER_SUCCESS:
            continue
        logs_to_revert = reg.registered_from.logs.filter(date__gt=reg.registered_date).exclude(action__in=LOG_WHITELIST)
        if len(permissible_addons) == 1:
            assert not logs_to_revert.exclude(action__in=LOG_GREYLIST).exists(), f'{registration._id}: {reg.registered_from._id} had unexpected unacceptable logs'
        else:
            assert not logs_to_revert.exclude(action__in=LOG_GREYLIST).exclude(action__in=PERMISSIBLE_BLACKLIST).exists(), f'{registration._id}: {reg.registered_from._id} had unexpected unacceptable logs'
        logger.info(f'Preparing to archive {reg._id}')
        for short_name in permissible_addons:
            node_settings = reg.registered_from.get_addon(short_name)
            if not hasattr(node_settings, '_get_file_tree'):
                # Excludes invalid or None-type
                continue
            if not node_settings.configured:
                if not allow_unconfigured:
                    raise Exception(f'{reg._id}: {short_name} on {reg.registered_from._id} is not configured. If this is permissible, re-run with `--allow-unconfigured`.')
                continue
            if not reg.archive_job.get_target(short_name) or reg.archive_job.get_target(short_name).status == ARCHIVER_SUCCESS:
                continue
            if short_name == 'osfstorage':
                file_tree = build_file_tree(reg, node_settings, permissible_addons=permissible_addons)
                manually_archive(file_tree, reg, node_settings)
                complete_archive_target(reg, short_name)
            else:
                assert reg.archiving, f'{reg._id}: Must be `archiving` for WB to copy'
                perform_wb_copy(reg, node_settings, *args, **kwargs)

def archive_registrations(*args, **kwargs):
    for reg in deepcopy(VERIFIED):
        archive(reg, *args, *kwargs)
        ARCHIVED.append(reg)
        VERIFIED.remove(reg)

def verify(registration, permissible_addons=DEFAULT_PERMISSIBLE_ADDONS, raise_error=False):
    permissible_addons = set(permissible_addons)
    maybe_suppress_error = contextlib.suppress(ValidationError) if not raise_error else contextlib.nullcontext(enter_result=False)

    for reg in registration.node_and_primary_descendants():
        logger.info(f'Verifying {reg._id}')
        if reg.archive_job.status == ARCHIVER_SUCCESS:
            continue
        nonignorable_logs = get_logs_to_revert(reg)
        unacceptable_logs = nonignorable_logs.exclude(action__in=LOG_GREYLIST)
        if unacceptable_logs.exists():
            if len(permissible_addons) == 1 or unacceptable_logs.exclude(action__in=PERMISSIBLE_BLACKLIST):
                message = '{}: Original node {} has unacceptable logs: {}'.format(
                    registration._id,
                    reg.registered_from._id,
                    list(unacceptable_logs.values_list('action', flat=True))
                )
                logger.error(message)

                with maybe_suppress_error:
                    raise ValidationError(message)

                return False
        if nonignorable_logs.filter(action__in=VERIFY_PROVIDER).exists():
            for log in nonignorable_logs.filter(action__in=VERIFY_PROVIDER):
                for key in ['source', 'destination']:
                    if key in log.params:
                        if log.params[key]['provider'] != 'osfstorage':
                            message = '{}: {} Only OSFS moves and renames are permissible'.format(
                                registration._id,
                                log._id
                            )
                            logger.error(message)

                            with maybe_suppress_error:
                                raise ValidationError(message)

                            return False
        addons = reg.registered_from.get_addon_names()
        if set(addons) - set(permissible_addons | {'wiki'}) != set():
            message = f'{registration._id}: Original node {reg.registered_from._id} has addons: {addons}'
            logger.error(message)

            with maybe_suppress_error:
                raise ValidationError(message)

            return False
        if nonignorable_logs.exists():
            logger.info('{}: Original node {} has had revertable file operations'.format(
                registration._id,
                reg.registered_from._id
            ))
        if reg.registered_from.is_deleted:
            logger.info('{}: Original node {} is deleted'.format(
                registration._id,
                reg.registered_from._id
            ))
    return True

def verify_registrations(registration_ids, permissible_addons):
    for r_id in registration_ids:
        reg = Registration.load(r_id)
        if not reg:
            logger.warning(f'Registration {r_id} not found')
        else:
            if verify(reg, permissible_addons=permissible_addons):
                VERIFIED.append(reg)
            else:
                SKIPPED.append(reg)

def check(reg):
    """Check registration status. Raise exception if registration stuck."""
    logger.info(f'Checking {reg._id}')
    if reg.is_deleted:
        return f'Registration {reg._id} is deleted.'

    expired_if_before = timezone.now() - ARCHIVE_TIMEOUT_TIMEDELTA
    archive_job = reg.archive_job
    root_job = reg.root.archive_job
    archive_tree_finished = archive_job.archive_tree_finished()

    if type(archive_tree_finished) is int:
        still_archiving = archive_tree_finished != len(archive_job.children)
    else:
        still_archiving = not archive_tree_finished
    if still_archiving and root_job.datetime_initiated < expired_if_before:
        logger.warning(f'Registration {reg._id} is stuck in archiving')
        if verify(reg):
            raise RegistrationStuckRecoverableException(f'Registration {reg._id} is stuck and verified recoverable')
        else:
            raise RegistrationStuckBrokenException(f'Registration {reg._id} is stuck and verified broken')

    return f'Registration {reg._id} is not stuck in archiving'

def check_registrations(registration_ids):
    for r_id in registration_ids:
        reg = Registration.load(r_id)
        if not reg:
            logger.warning(f'Registration {r_id} not found')
        else:
            try:
                status = check(reg)
                logger.info(status)
                CHECKED_OKAY.append(reg)
            except RegistrationStuckRecoverableException as exc:
                logger.info(str(exc))
                CHECKED_STUCK_RECOVERABLE.append(reg)
            except RegistrationStuckBrokenException as exc:
                logger.info(str(exc))
                CHECKED_STUCK_BROKEN.append(reg)

def log_results(dry_run):
    if CHECKED_OKAY:
        logger.info(f'{len(CHECKED_OKAY)} registrations not stuck: {[e._id for e in CHECKED_OKAY]}')
    if CHECKED_STUCK_RECOVERABLE:
        logger.info(f'{len(CHECKED_STUCK_RECOVERABLE)} registrations stuck but recoverable: {[e._id for e in CHECKED_STUCK_RECOVERABLE]}')
    if CHECKED_STUCK_BROKEN:
        logger.warning(f'{len(CHECKED_STUCK_BROKEN)} registrations stuck and unrecoverable: {[e._id for e in CHECKED_STUCK_BROKEN]}')

    if VERIFIED:
        logger.info('{} registrations verified: {}'.format(
            len(VERIFIED),
            [e._id for e in VERIFIED],
        ))
    if ARCHIVED:
        logger.info('{} registrations archived: {}'.format(
            len(ARCHIVED),
            [e._id for e in ARCHIVED]
        ))
    if SKIPPED:
        logger.error(f'{len(SKIPPED)} registrations skipped: {[e._id for e in SKIPPED]}')

class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            dest='check',
            help='Check if registrations are stuck',
        )
        parser.add_argument(
            '--delete-collisions',
            action='store_true',
            dest='delete_collisions',
            help='Specifies that colliding archive filenodes should be deleted and re-archived in the event of a collision',
        )
        parser.add_argument(
            '--skip-collisions',
            action='store_true',
            dest='skip_collisions',
            help='Specifies that colliding archive filenodes should be skipped and the archive job target marked as successful in the event of a collision',
        )
        parser.add_argument(
            '--allow-unconfigured',
            action='store_true',
            dest='allow_unconfigured',
            help='Specifies that addons with a False `configured` property are to be skipped, rather than raising an error',
        )
        parser.add_argument('--addons', type=str, nargs='*', help='Addons other than OSFStorage to archive. Use caution')
        parser.add_argument('--guids', type=str, nargs='+', help='GUIDs of registrations to archive')

    def handle(self, *args, **options):
        delete_collisions = options.get('delete_collisions')
        skip_collisions = options.get('skip_collisions')
        allow_unconfigured = options.get('allow_unconfigured')
        if delete_collisions and skip_collisions:
            raise Exception('Cannot specify both delete_collisions and skip_collisions')

        dry_run = options.get('dry_run')
        if not dry_run:
            script_utils.add_file_logger(logger, __file__)

        addons = options.get('addons') or set()
        addons.update(DEFAULT_PERMISSIBLE_ADDONS)

        registration_ids = options.get('guids', [])

        if options.get('check', False):
            check_registrations(registration_ids)
        else:
            verify_registrations(registration_ids, permissible_addons=addons)
            if not dry_run:
                archive_registrations(
                    permissible_addons=addons,
                    delete_collisions=delete_collisions,
                    skip_collisions=skip_collisions,
                    allow_unconfigured=allow_unconfigured,
                )

        log_results(dry_run)
