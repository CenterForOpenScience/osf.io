from website.addons.osffiles.exceptions import FileNotFoundError


def urlsafe_filename(filename):
    #FIXME: encoding the filename this way is flawed. For instance - foo.bar resolves to the same string as foo_bar.
    return filename.replace('.', '_')

def get_versions(filename, node):
    """Return IDs for a file's version records.

    :param str filename: The name of the file.
    :param Node node: The node which has the requested file.
    :return: List of ids (strings) for :class:`NodeFile` records.

    :raises: FileNotFoundError if file does not exists for the node.
    """
    try:
        return node.files_versions[urlsafe_filename(filename)]
    except KeyError:
        raise FileNotFoundError('{0!r} not found for node {1!r}'.format(
            filename, node._id
        ))


def get_latest_version_number(filename, node):
    """Return the current version number (0-indexed) for a file.

    :param str filename: The name of the file.
    :param Node node: The node which has the requested file.

    :raises: FileNotFoundError if file does not exists for the node.
    """
    versions = get_versions(filename, node)
    return len(versions) - 1
