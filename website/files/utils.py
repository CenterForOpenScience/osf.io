
def copy_files(src, target_node, parent=None, name=None):
    """Copy the files from src to the target node
    :param Folder src: The source to copy children from
    :param Node target_node: The node settings of the project to copy files to
    :param Folder parent: The parent of to attach the clone of src to, if applicable
    """
    assert not parent or not parent.is_file, 'Parent must be a folder'

    cloned = src.clone()
    cloned.parent = parent
    cloned.target = target_node
    cloned.name = name or cloned.name
    cloned.copied_from = src

    cloned.save()

    if src.is_file and src.versions.exists():
        cloned.versions.add(*src.versions.all())

    if not src.is_file:
        for child in src.children:
            copy_files(child, target_node, parent=cloned)

    return cloned
