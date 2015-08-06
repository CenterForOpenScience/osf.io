import requests

from website import settings

INDEXED_TYPES = (
    '.txt',
    '.md',
    '.rtf',
    '.docx',
    '.pdf',
)

def require_file_indexing(func):
    """ Execute function only if use_file_indexing setting is true. """
    def wrapper(*args, **kwargs):
        if settings.USE_FILE_INDEXING:
            return func(*args, **kwargs)
        return None
    return wrapper


def is_indexed(file_node):
    """ Return true if the file is to be indexed. """
    addon = file_node.node_settings
    if not addon.config.short_name == 'osfstorage':
        return False
    if not name_is_indexed(file_node.name):
        return False
    return True


def name_is_indexed(file_name):
    if not file_name.endswith(INDEXED_TYPES):
        return False
    return True


def get_file_content(file_node):
    """ Return the content of the file node. """
    file_, _ = file_node.node_settings.find_or_create_file_guid(file_node.path)
    url = file_.download_url + '&mode=render'
    response = requests.get(url)
    return response.content


def get_file_size(file_node):
    """ Return the size of the file. """
    file_, _ = file_node.node_settings.find_or_create_file_guid(file_node.path)
    file_.enrich()
    return file_.size


def norm_path(path):
    """ Return the path without a leading forward slash. """
    return path if not path[0] == '/' else path[1:]


def build_file_document(file_node, include_content=True):
    """ Return file data to be in the indexed document as a dict.

    :param name: Name of file.
    :param path: Path of file.
    :param addon: Instance of storage addon containing the containing the file.
    :param include_content: Include the content of the file in document.
    """
    name = file_node.name
    parent_node = file_node.node
    parent_id = parent_node._id
    path = norm_path(file_node.path)

    file_size = get_file_size(file_node)
    file_content = get_file_content(file_node) if include_content else None

    return {
        'name': name,
        'path': path,
        'content': file_content,
        'parent_id': parent_id,
        'size': file_size,
    }


def collect_files_from_filenode(file_node):
    children = [] if file_node.is_file else file_node.children
    if file_node.is_file:
        yield file_node

    for child in children:
        if file_node.is_folder:
            for file_ in collect_files_from_filenode(child):
                yield file_
        elif file_node.is_file:
            yield file_node


def collect_files(node):
    osf_addon = node.get_addon('osfstorage')
    root_node = osf_addon.root_node

    if not node.is_public:
        raise StopIteration

    for file_node in collect_files_from_filenode(root_node):
            yield file_node

    for component_node in node.nodes:
        for file_node in collect_files(component_node):
            yield file_node
