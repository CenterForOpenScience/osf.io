from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public

@must_be_contributor_or_public
@must_have_addon('gdrive', 'node')
def gdrive_view_file(path, node_addon, auth, **kwargs):
    """Web view for the file detail page."""
    # if not path:
    #     raise HTTPError(http.NOT_FOUND)
    # # check that current user has access to the path
    # if not is_authorizer(auth, node_addon):
    #     abort_if_not_subdir(path, node_addon.folder)
    # node = node_addon.owner
    # client = get_node_addon_client(node_addon)
    # # Lazily create a file GUID record
    # file_obj, created = DropboxFile.get_or_create(node=node, path=path)
    #
    # redirect_url = check_file_guid(file_obj)
    # if redirect_url:
    #     return redirect(redirect_url)
    # rev = request.args.get('rev') or ''
    # rendered = render_dropbox_file(file_obj, client=client, rev=rev)
    # cleaned_path = clean_path(path)
    # response = {
    #     'revisions_url': node.api_url_for('dropbox_get_revisions',
    #         path=cleaned_path, rev=rev),  # Append current revision as a query param
    #     'file_name': get_file_name(path),
    #     'render_url': node.api_url_for('dropbox_render_file', path=cleaned_path),
    #     'download_url': file_obj.download_url(guid=True, rev=rev),
    #     'rendered': rendered,
    # }
    # response.update(serialize_node(node, auth, primary=True))
    # return response, http.OK
    pass
