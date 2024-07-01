import functools
import unicodedata

from collections import defaultdict
from django.db.models import CharField, OuterRef, Subquery
from framework.auth import Auth
from framework.utils import sanitize_html

from website import (
    mails,
    settings
)
from website.archiver import (
    StatResult, AggregateStatResult,
    ARCHIVER_NETWORK_ERROR,
    ARCHIVER_SIZE_EXCEEDED,
    ARCHIVER_FILE_NOT_FOUND,
    ARCHIVER_FORCED_FAILURE,
)

FILE_HTML_LINK_TEMPLATE = settings.DOMAIN + 'project/{registration_guid}/files/osfstorage/{file_id}'
FILE_DOWNLOAD_LINK_TEMPLATE = settings.DOMAIN + 'download/{file_id}'

def normalize_unicode_filenames(filename):
    return [
        sanitize_html(unicodedata.normalize(form, filename)).replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        for form in ['NFD', 'NFC']
    ]


def send_archiver_size_exceeded_mails(src, user, stat_result, url):
    mails.send_mail(
        to_addr=settings.OSF_SUPPORT_EMAIL,
        mail=mails.ARCHIVE_SIZE_EXCEEDED_DESK,
        user=user,
        src=src,
        stat_result=stat_result,
        can_change_preferences=False,
        url=url,
    )
    mails.send_mail(
        to_addr=user.username,
        mail=mails.ARCHIVE_SIZE_EXCEEDED_USER,
        user=user,
        src=src,
        can_change_preferences=False,
    )


def send_archiver_copy_error_mails(src, user, results, url):
    mails.send_mail(
        to_addr=settings.OSF_SUPPORT_EMAIL,
        mail=mails.ARCHIVE_COPY_ERROR_DESK,
        user=user,
        src=src,
        results=results,
        url=url,
        can_change_preferences=False,
    )
    mails.send_mail(
        to_addr=user.username,
        mail=mails.ARCHIVE_COPY_ERROR_USER,
        user=user,
        src=src,
        results=results,
        can_change_preferences=False,
    )

def send_archiver_file_not_found_mails(src, user, results, url):
    mails.send_mail(
        to_addr=settings.OSF_SUPPORT_EMAIL,
        mail=mails.ARCHIVE_FILE_NOT_FOUND_DESK,
        can_change_preferences=False,
        user=user,
        src=src,
        results=results,
        url=url,
    )
    mails.send_mail(
        to_addr=user.username,
        mail=mails.ARCHIVE_FILE_NOT_FOUND_USER,
        user=user,
        src=src,
        results=results,
        can_change_preferences=False,
    )

def send_archiver_uncaught_error_mails(src, user, results, url):
    mails.send_mail(
        to_addr=settings.OSF_SUPPORT_EMAIL,
        mail=mails.ARCHIVE_UNCAUGHT_ERROR_DESK,
        user=user,
        src=src,
        results=results,
        can_change_preferences=False,
        url=url,
    )
    mails.send_mail(
        to_addr=user.username,
        mail=mails.ARCHIVE_UNCAUGHT_ERROR_USER,
        user=user,
        src=src,
        results=results,
        can_change_preferences=False,
    )


def handle_archive_fail(reason, src, dst, user, result):
    url = settings.INTERNAL_DOMAIN + src._id
    if reason == ARCHIVER_NETWORK_ERROR:
        send_archiver_copy_error_mails(src, user, result, url)
    elif reason == ARCHIVER_SIZE_EXCEEDED:
        send_archiver_size_exceeded_mails(src, user, result, url)
    elif reason == ARCHIVER_FILE_NOT_FOUND:
        send_archiver_file_not_found_mails(src, user, result, url)
    elif reason == ARCHIVER_FORCED_FAILURE:  # Forced failure using scripts.force_fail_registration
        pass
    else:  # reason == ARCHIVER_UNCAUGHT_ERROR
        send_archiver_uncaught_error_mails(src, user, result, url)
    if dst.root.sanction:
        dst.root.sanction.forcibly_reject()
        dst.root.sanction.save()
    dst.root.delete_registration_tree(save=True)

def archive_provider_for(node, user):
    """A generic function to get the archive provider for some node, user pair.

    :param node: target node
    :param user: target user (currently unused, but left in for future-proofing
    the code for use with archive providers other than OSF Storage)
    """
    return node.get_addon(settings.ARCHIVE_PROVIDER)

def has_archive_provider(node, user):
    """A generic function for checking whether or not some node, user pair has
    an attached provider for archiving

    :param node: target node
    :param user: target user (currently unused, but left in for future-proofing
    the code for use with archive providers other than OSF Storage)
    """
    return node.has_addon(settings.ARCHIVE_PROVIDER)

def link_archive_provider(node, user):
    """A generic function for linking some node, user pair with the configured
    archive provider

    :param node: target node
    :param user: target user (currently unused, but left in for future-proofing
    the code for use with archive providers other than OSF Storage)
    """
    addon = node.get_or_add_addon(settings.ARCHIVE_PROVIDER, auth=Auth(user), log=False)
    if hasattr(addon, 'on_add'):
        addon.on_add()
    node.save()

def aggregate_file_tree_metadata(addon_short_name, fileobj_metadata, user):
    """Recursively traverse the addon's file tree and collect metadata in AggregateStatResult

    :param src_addon: AddonNodeSettings instance of addon being examined
    :param fileobj_metadata: file or folder metadata of current point of reference
    in file tree
    :param user: archive initatior
    :return: top-most recursive call returns AggregateStatResult containing addon file tree metadata
    """
    disk_usage = fileobj_metadata.get('size')
    if fileobj_metadata['kind'] == 'file':
        result = StatResult(
            target_name=normalize_unicode_filenames(fileobj_metadata['name'])[0],
            target_id=fileobj_metadata['path'].lstrip('/'),
            disk_usage=disk_usage or 0,
        )
        return result
    else:
        return AggregateStatResult(
            target_id=fileobj_metadata['path'].lstrip('/'),
            target_name=normalize_unicode_filenames(fileobj_metadata['name'])[0],
            targets=[aggregate_file_tree_metadata(addon_short_name, child, user) for child in fileobj_metadata.get('children', [])],
        )

def before_archive(node, user):
    from osf.models import ArchiveJob
    link_archive_provider(node, user)
    job = ArchiveJob.objects.create(
        src_node=node.registered_from,
        dst_node=node,
        initiator=user
    )
    job.set_targets()

def _do_get_file_map(file_tree):
    """Reduces a tree of folders and files into a list of (<sha256>, <file_metadata>) pairs
    """
    file_map = []
    stack = [file_tree]
    while len(stack):
        tree_node = stack.pop(0)
        if tree_node['kind'] == 'file':
            file_map.append((tree_node['extra']['hashes']['sha256'], tree_node))
        else:
            stack = stack + tree_node['children']
    return file_map

def _memoize_get_file_map(func):
    cache = {}

    @functools.wraps(func)
    def wrapper(node):
        from osf.models import OSFUser
        if node._id not in cache:
            osf_storage = node.get_addon('osfstorage')
            file_tree = osf_storage._get_file_tree(user=OSFUser.load(list(node.admin_contributor_or_group_member_ids)[0]))
            cache[node._id] = _do_get_file_map(file_tree)
        return func(node, cache[node._id])
    return wrapper

@_memoize_get_file_map
def get_file_map(node, file_map):
    """
    note:: file_map is injected implictly by the decorator; this method is called like:

    get_file_map(node)
    """
    for (key, value) in file_map:
        yield (key, value, node._id)
    for child in node.nodes_primary:
        for key, value, node_id in get_file_map(child):
            yield (key, value, node_id)


def get_title_for_question(schema, qid):
    annotated_blocks = schema.schema_blocks.filter(
        block_type='question-label'
    ).annotate(
        qid=Subquery(
            schema.schema_blocks.filter(
                schema_block_group_key=OuterRef('schema_block_group_key'),
                registration_response_key__isnull=False
            ).values('registration_response_key')[:1],
            output_field=CharField()
        )
    )

    return annotated_blocks.get(qid=qid).display_text


def migrate_file_metadata(dst):
    if dst.root_id != dst.id:
        return

    schema = dst.registration_schema
    file_input_qids = schema.schema_blocks.filter(
        block_type='file-input'
    ).values_list('registration_response_key', flat=True)
    if not file_input_qids:
        return

    file_response_keys_by_hash = _get_file_response_hashes(dst, file_input_qids)
    updated_file_responses = _get_updated_file_references(dst, file_response_keys_by_hash)

    _validate_updated_responses(dst, file_input_qids, updated_file_responses)

    for qid, updated_response in updated_file_responses.items():
        response_block = dst.schema_responses.get().response_blocks.get(schema_key=qid)
        response_block.set_response(updated_response)

    dst.registration_responses = dst.schema_responses.get().all_responses
    dst.registered_meta[schema._id] = dst.expand_registration_responses()
    dst.save()


def _get_file_response_hashes(registration, file_input_qids):
    '''Extract the sha256 hashes for all file responses on the registration.

    Returns a dictionary mapping the hashes to a list of qids where the file
    was found in the registration's responses, i,e,:
    {hash1: [q1], hash2: [q1, q5], hash3: [q5] . . .}
    '''
    file_response_keys_by_hash = defaultdict(list)
    file_responses = {
        qid: registration.registration_responses.get(qid, []) for qid in file_input_qids
    }
    for qid, response in file_responses.items():
        for file_info in response:
            file_response_keys_by_hash[file_info['file_hashes']['sha256']].append(qid)

    return file_response_keys_by_hash


def _get_updated_file_references(registration, file_response_keys_by_hash):
    '''Loop through archived files to get the updated references for the registration responses.

    Returns a dictionary mapping each qid to its list of updated responses
    '''
    from osf.models import Guid
    original_responses = registration.schema_responses.get().all_responses
    updated_file_responses = defaultdict(list)
    previous_node_id = ''
    for file_sha, file_info, archived_node_id in get_file_map(registration):
        # cache the guid of the source project for the current file tree
        if archived_node_id != previous_node_id:
            previous_node_id = archived_node_id
            source_project_id = Guid.objects.get(_id=archived_node_id).referent.registered_from._id

        if file_sha in file_response_keys_by_hash:
            response_value = _make_file_response(file_info, archived_node_id)
            for qid in file_response_keys_by_hash[file_sha]:
                # Handle the case where the same file exists in multiple components
                original_response = _get_response_entry_for_hash(original_responses, qid, file_sha)
                normalized_original_file_name = normalize_unicode_filenames(original_response['file_name'])[0]
                if (
                    source_project_id in original_response['file_urls']['html']
                    and response_value['file_name'] == normalized_original_file_name
                ):
                    updated_file_responses[qid].append(response_value)

    return updated_file_responses


def _get_response_entry_for_hash(response_dict, qid, file_hash):
    for entry in response_dict[qid]:
        if entry['file_hashes']['sha256'] == file_hash:
            return entry
    return None


def _make_file_response(file_info, parent_guid):
    '''Generate the dictionary for an entry in a 'file-input' block response.'''
    archived_file_id = file_info['path'].lstrip('/')
    return {
        'file_id': archived_file_id,
        'file_name': normalize_unicode_filenames(file_info['name'])[0],
        'file_urls': {
            'html':
                FILE_HTML_LINK_TEMPLATE.format(
                    registration_guid=parent_guid, file_id=archived_file_id
                ),
            'download':
                FILE_DOWNLOAD_LINK_TEMPLATE.format(file_id=archived_file_id)
        },
        'file_hashes': {'sha256': file_info['extra']['hashes']['sha256']}
    }


def _validate_updated_responses(registration, file_input_qids, updated_responses):
    '''Confirm that every file response has an updated value and that nothing fishy happened.'''
    schema = registration.registration_schema
    missing_responses = []
    for qid in file_input_qids:
        question_title = ''
        for entry in registration.registration_responses.get(qid, []):
            file_name = entry['file_name']
            file_hash = entry['file_hashes']['sha256']
            matching_entry = _get_response_entry_for_hash(updated_responses, qid, file_hash)
            if not matching_entry:
                question_title = question_title or get_title_for_question(schema, qid)
                missing_responses.append({'file_name': file_name, 'question_title': question_title})

    if missing_responses:
        from website.archiver.tasks import ArchivedFileNotFound
        raise ArchivedFileNotFound(
            registration=registration,
            missing_files=missing_responses
        )
