from website.addons.osffiles.exceptions import FileNotFoundError

def get_current_file_version(filename, node):
    """Return the current version number (0-indexed) for a NodeFile.

    :raises: FileNotFoundError if file does not exists for the node.
    """
    try:
        versions = node.files_versions[filename.replace('.', '_')]
    except KeyError:
        raise FileNotFoundError('{0!r} not found for node {1!r}'.format(
            filename, node._id
        ))
    return len(versions) - 1
