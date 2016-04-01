# MODEL MESSAGES :model.py
BEFORE_PAGE_LOAD_PRIVATE_NODE_MIXED_FS = 'Warning: This OSF {category} is private but figshare project {project_id} may contain some public files or filesets.'

BEFORE_PAGE_LOAD_PUBLIC_NODE_MIXED_FS = 'Warning: This OSF {category} is public but figshare project {project_id} may contain some private files or filesets.'

BEFORE_PAGE_LOAD_PERM_MISMATCH = 'Warning: This OSF {category} is {node_perm}, but the figshare article {figshare_id} is {figshare_perm}. '

BEFORE_PAGE_LOAD_PUBLIC_NODE_PRIVATE_FS = 'Users can view the contents of this private figshare article. '

BEFORE_REMOVE_CONTRIBUTOR = 'The figshare add-on for this {category} is authenticated by {user}. Removing this user will also remove write access to the {category} unless another contributor re-authenticates. '

BEFORE_FORK_OWNER = 'Because you have authenticated the figshare add-on for this {category}, forking it will also transfer your authorization to the forked {category}. '

BEFORE_FORK_NOT_OWNER = 'Because this figshare add-on has been authenticated by a different user, forking it will not transfer authentication to the forked {category}. '

AFTER_FORK_OWNER = 'figshare authorization copied to forked {category}. '

AFTER_FORK_NOT_OWNER = 'figshare authorization not copied to forked {category}. You may authorize this fork on the <u><a href={url}>Settings</a></u> page. '

BEFORE_REGISTER = 'The contents of figshare projects cannot be registered at this time. The figshare data associated with this {category} will not be included as part of this registration. '
# END MODEL MESSAGES

# MFR MESSAGES :views/crud.py
FIGSHARE_VIEW_FILE_PRIVATE = 'Since this figshare file is unpublished we cannot render it. In order to access this content you will need to log into the <u><a href="{url}">figshare page</a></u> and view it there. '

FIGSHARE_VIEW_FILE_OVERSIZED = 'This figshare file is too large to render; <u><a href="{url}">download file</a></u> to view it. '

'''
Publishing this article is an irreversible operation. Once a figshare article is published it can never be deleted. Proceed with caution.
<br /><br />
Also, figshare requires some additional info before this article can be published: <br />
<form id='figsharePublishForm' action='${nodeApiUrl}figshare/publish/article/${parent_id}/'>
    <h3><label><Title></label></h3>
    <input name='title' type='text' value='${figshare_title}'>
    <h3><label>Category:</label></h3>
    <select name='cat' id='figshareCategory' value='${figshare_category}'>${figshare_categories}</select><br />
    <h3><label>Tag(s):</label></h3>
    <input name='tags' type='text' value='${figshare_tags}' placeholder='e.g. neuroscience, cognition'><br />
    <h3><label>Description</label></h3>
    <textarea name='description' placeholder='Please type a description of this file here'>${figshare_desc}</textarea>
</form>
'''

OAUTH_INVALID = 'Your OAuth key for figshare is no longer valid. Please re-authenticate. '

# END MFR MESSAGES
