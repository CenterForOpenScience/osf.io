import logging
import requests

from website import settings


logger = logging.getLogger(__name__)


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
        logger.info('File indexing not enabled.')
    return wrapper


def is_indexed(file_node):
    """ Return true if the file is to be indexed. """
    addon = file_node.node_settings
    if not addon.config.short_name == 'osfstorage':
        return False
    return file_node.name.endswith(INDEXED_TYPES)


def get_file_content(file_node):
    """ Return the content of the file node. """
    url = get_file_content_url(file_node)
    response = requests.get(url)
    return response.content


def get_file_content_url(file_node):
    """ Return the url from which content can be downloaded """
    file_, _ = file_node.node_settings.find_or_create_file_guid(file_node.path)
    url = file_.download_url + '&mode=render'
    return url


def get_file_size(file_node):
    """ Return the size of a file in bytes. """
    latest_version = file_node.get_version()
    return latest_version.size


def norm_path(path):
    """ Return the path without a leading forward slash. """
    return path if not path[0] == '/' else path[1:]


def collect_files_from_filenode(file_node):
    """ Generate the file nodes child files. """
    children = [] if file_node.is_file else file_node.children
    if file_node.is_file:
        yield file_node

    for child in children:
        for file_ in collect_files_from_filenode(child):
            yield file_


def collect_files(node, recur=True):
    """ Generate the files under the given node.

    :param recur: If true recursively returns the files under child nodes.
    """
    osf_addon = node.get_addon('osfstorage')
    root_node = osf_addon.root_node

    if not node.is_public:
        raise StopIteration

    for file_node in collect_files_from_filenode(root_node):
            yield file_node

    if recur:
        for component_node in node.nodes:
            for file_node in collect_files(component_node):
                yield file_node
