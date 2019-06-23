
def copy_files(src, target_node, parent=None, name=None):
    """Copy the files from src to the target node
    :param Folder src: The source to copy children from
    :param Node target_node: The node to copy files to
    :param Folder parent: The parent of to attach the clone of src to, if applicable
    """
    assert not parent or not parent.is_file, 'Parent must be a folder'
    renaming = src.name != name

    cloned = src.clone()
    cloned.parent = parent
    cloned.target = target_node
    cloned.name = name or cloned.name
    cloned.copied_from = src

    cloned.save()
    if src.is_file and src.versions.exists():
        fileversions = src.versions.select_related('region').order_by('-created')
        most_recent_fileversion = fileversions.first()
        if most_recent_fileversion.region and most_recent_fileversion.region != target_node.osfstorage_region:
            # add all original version except the most recent
            attach_versions(cloned, fileversions[1:], src)
            # create a new most recent version and update the region before adding
            new_fileversion = most_recent_fileversion.clone()
            new_fileversion.region = target_node.osfstorage_region
            new_fileversion.save()
            attach_versions(cloned, [new_fileversion], src)
        else:
            attach_versions(cloned, src.versions.all(), src)

        if renaming:
            latest_version = cloned.versions.first()
            node_file_version = latest_version.get_basefilenode_version(cloned)
            # If this is a copy and a rename, update the name on the through table
            node_file_version.version_name = cloned.name
            node_file_version.save()

        # copy over file metadata records
        if cloned.provider == 'osfstorage':
            for record in cloned.records.all():
                record.metadata = src.records.get(schema__name=record.schema.name).metadata
                record.save()

    if not src.is_file:
        for child in src.children:
            copy_files(child, target_node, parent=cloned)

    return cloned

def attach_versions(file, versions_list, src=None):
    """
    Loops through all versions in the versions list and attaches them to the file.
    Fetches the name associated with the versions on the original src, if copying.
    """
    for version in versions_list:
        original_version = version.get_basefilenode_version(src)
        name = original_version.version_name if original_version else None
        file.add_version(version, name)
