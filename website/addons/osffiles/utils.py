from website.addons.osffiles.exceptions import FileNotFoundError


def get_versions(filename, node):
    """Return file versions for a :class:`NodeFile`.

    :raises: FileNotFoundError if file does not exists for the node.
    """
    try:
        return node.files_versions[filename.replace('.', '_')]
    except KeyError:
        raise FileNotFoundError('{0!r} not found for node {1!r}'.format(
            filename, node._id
        ))


def get_latest_version_number(filename, node):
    """Return the current version number (0-indexed) for a NodeFile.

    :raises: FileNotFoundError if file does not exists for the node.
    """
    versions = get_versions(filename, node)
    return len(versions) - 1
