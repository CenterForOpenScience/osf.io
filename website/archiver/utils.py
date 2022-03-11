import functools

from collections import defaultdict

from framework.auth import Auth

from website.archiver import (
    StatResult, AggregateStatResult,
    ARCHIVER_NETWORK_ERROR,
    ARCHIVER_SIZE_EXCEEDED,
    ARCHIVER_FILE_NOT_FOUND,
    ARCHIVER_FORCED_FAILURE,
)

from website import (
    mails,
    settings
)
from osf.utils.sanitize import unescape_entities


FILE_HTML_LINK_TEMPLATE = 'https://staging.osf.io/project/{registration_guid}/files/osfstorage/{file_id}'
FILE_DOWNLOAD_LINK_TEMPLATE = 'https://staging.osf.io/download/{file_id}'

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
            target_name=fileobj_metadata['name'],
            target_id=fileobj_metadata['path'].lstrip('/'),
            disk_usage=disk_usage or 0,
        )
        return result
    else:
        return AggregateStatResult(
            target_id=fileobj_metadata['path'].lstrip('/'),
            target_name=fileobj_metadata['name'],
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

def find_registration_file(value, node):
    """
    some annotations:

    - `value` is  the `extra` from a file upload in `registered_meta`
        (see `Uploader.addFile` in website/static/js/registrationEditorExtensions.js)
    - `node` is a Registration instance
    - returns a `(file_info, node_id)` or `(None, None)` tuple, where `file_info` is from waterbutler's api
        (see `addons.base.models.BaseStorageAddon._get_fileobj_child_metadata` and `waterbutler.core.metadata.BaseMetadata`)
    """
    from osf.models import AbstractNode
    orig_sha256 = value['sha256']
    orig_name = unescape_entities(
        value['selectedFileName'],
        safe={
            '&lt;': '<',
            '&gt;': '>'
        }
    )
    orig_node = value['nodeId']
    file_map = get_file_map(node)
    for sha256, file_info, node_id in file_map:
        registered_from_id = AbstractNode.load(node_id).registered_from._id
        if sha256 == orig_sha256 and registered_from_id == orig_node and orig_name == file_info['name']:
            return file_info, node_id
    return None, None

def find_registration_files(values, node):
    """
    some annotations:

    - `values` is from `registered_meta`, e.g. `{ comments: [], value: '', extra: [] }`
    - `node` is a Registration model instance
    - returns a list of `(file_info, node_id, index)` or `(None, None, index)` tuples,
        where `file_info` is from `find_registration_file` above
    """
    ret = []
    for i in range(len(values.get('extra', []))):
        ret.append(find_registration_file(values['extra'][i], node) + (i,))
    return ret

def get_title_for_question(schema, path):
    path = path.split('.')
    root = path.pop(0)
    item = None
    for page in schema['pages']:
        questions = {
            q['qid']: q
            for q in page['questions']
        }
        if root in questions:
            item = questions[root]
    title = item.get('title')
    while len(path):
        item = item.get(path.pop(0), {})
        title = item.get('title', title)
    return title

def find_selected_files(schema, metadata):
    """
    some annotations:

    - `schema` is a RegistrationSchema instance
    - `metadata` is from `registered_meta` (for the given schema)
    - returns a dict that maps from each `osf-upload` question id (`.`-delimited path) to its chunk of metadata,
        e.g. `{ 'q1.uploader': { comments: [], extra: [...], value: 'foo.pdf' } }`
    """
    targets = []
    paths = [('', p) for p in schema.schema['pages']]

    while len(paths):
        prefix, path = paths.pop(0)
        if path.get('questions'):
            paths = paths + [('', q) for q in path['questions']]
        elif path.get('type'):
            qid = path.get('qid', path.get('id'))
            if path['type'] == 'object':
                paths = paths + [('{}.{}.value'.format(prefix, qid), p) for p in path['properties']]
            elif path['type'] == 'osf-upload':
                targets.append('{}.{}'.format(prefix, qid).lstrip('.'))
    selected = {}
    for t in targets:
        parts = t.split('.')
        value = metadata.get(parts.pop(0))
        while value and len(parts):
            value = value.get(parts.pop(0))
        if value:
            selected[t] = value
    return selected

VIEW_FILE_URL_TEMPLATE = '/project/{node_id}/files/osfstorage/{file_id}/'

def deep_get(obj, path):
    parts = path.split('.')
    item = obj
    key = None
    while len(parts):
        key = parts.pop(0)
        item[key] = item.get(key, {})
        item = item[key]
    return item


def _get_file_response_hashes(registration):
    '''Extract the sha256 hashes for all file responses on the registration.

    Returns a dictionary mapping the hashes to a (qid, index) tuple identifying where
    the file was found in the registration's registration_responses dictionary, i,e,:
    {hash1: (q1, 0), hash2: (q1, 1), hash3: (q5, 0) . . .}
    '''
    file_input_qids = registration.registration_schema.schema_blocks.filter(
        block_type='file-input'
    ).values_list(
        'registration_response_key',
        flat=True
    )

    file_responses = {qid: registration.registration_responses[qid] for qid in file_input_qids}
    file_hashes_to_responses = {}
    for qid, response in file_responses.items():
        for index, file_info in enumerate(response):
            file_hashes_to_responses[file_info['hashes']['sha256']] = (qid, index)


def _get_updated_file_references(registration, file_response_indices_by_hash):
    '''Loop through archived files to get the updated references for the registration responses.

    Returns a nested dictionary mapping the location of the attached file within the registration's
    registation_responses to a dictionary containing the new response value.
    '''
    updated_file_responses = defaultdict(dict)
    guid = registration._id

    discovered_files = set()
    for archived_file in registration.files.all():
        file_sha = archived_file.last_known_metadata['hashes']['sha256']
        if file_sha in file_response_indices_by_hash:
            discovered_files.add(file_sha)
            qid, index = file_response_indices_by_hash[file_sha]
            updated_file_responses[qid][index] = {
                'file_id': archived_file._id,
                'file_name': archived_file.name,
                'file_urls': {
                    'view':
                        FILE_HTML_LINK_TEMPLATE.format(
                            registration_guid=guid, file_id=archived_file._id
                        ),
                    'download':
                        FILE_DOWNLOAD_LINK_TEMPLATE.format(file_id=archived_file._id)
                },
                'file_hashes': {'sha256': file_sha}
            }

    missing_file_indices = [
        response_index for sha, response_index in file_response_indices_by_hash.items()
        if sha not in discovered_files
    ]
    return updated_file_responses, missing_file_indices


def migrate_file_metadata(dst, schema):
    file_response_indices_by_hash = _get_file_response_hashes(dst)
    updated_file_responses, missing_file_indices = (
        _get_updated_file_references(dst, file_response_indices_by_hash)
    )

    if missing_file_indices:
        from website.archiver.tasks import ArchivedFileNotFound
        raise ArchivedFileNotFound(
            registration=dst,
            missing_files=[
                dst.registration_responses[qid][index]['file_name']
                for qid, index in missing_file_indices
            ]
        )

    for qid in updated_file_responses:
        for subindex, updated_response in updated_file_responses[qid].items():
            dst.registration_resposnes[qid][subindex] = updated_response

    dst.registered_meta[schema._id] = dst.expand_registration_responses()
    if dst.root_id == dst.id:  # Also fix the initial SchemaResponse for root registrations
        dst.schema_responses.get()._update_file_references(dst.registration_responses)

    dst.save()
