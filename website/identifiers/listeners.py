from website.project import signals


@signals.node_deleted.connect
def update_status_on_delete(node):
    from website.identifiers.tasks import update_doi_metadata_on_change

    if node.get_identifier("doi"):
        update_doi_metadata_on_change(node._id)
