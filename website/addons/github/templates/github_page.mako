<%inherit file="project/addon/page.mako" />

% if user['can_edit']:

    % if not has_auth:

        <div class="alert alert-warning">
            This GitHub add-on has not been authorized. To enable file uploads and deletion,
            browse to the <a href="${node['url']}settings/">settings</a> page and authorize this add-on.
        </div>

    % elif not has_access:

        <div class="alert alert-warning">
            Your GitHub authorization does not have access to this repo. To enable file uploads
            and deletion, authorize using a GitHub account that has access to this repo, or
            ask one of its owners to grant access to your GitHub account.
        </div>

    % endif

% endif

<div class="row">

    <div class="col-md-6">

        <div>

            Viewing ${gh_user} / ${repo}

            % if len(branches) == 1:

                ${branches[0]['name']}

            % elif len(branches) > 1:

                <form role="form" style="display: inline;">
                    <select id="gitBranchSelect" name="branch">
                        % for _branch in branches:
                            <option
                                value=${_branch['name']}
                                ${'selected' if branch == _branch['name'] else ''}
                            >${_branch['name']}</option>
                        % endfor
                    </select>
                </form>

            % endif

        </div>

        % if sha:
            <p>Commit: ${sha}</p>
        % endif

    </div>

    <div class="col-md-6">

        <div>
            Download:
            <a href="${api_url}github/tarball/?ref=${ref}">Tarball</a>
            <span>|</span>
            <a href="${api_url}github/zipball/?ref=${ref}">Zip</a>
        </div>

    </div>

</div>

% if user['can_edit'] and has_auth:

    <div class="container" style="position: relative;">
        <h3 id="dropZoneHeader">Drag and drop (or <a href="#" id="gitFormUpload">click here</a>) to upload files</h3>
        <div id="fallback"></div>
        <div id="totalProgressActive" style="width: 35%; height: 20px; position: absolute; top: 73px; right: 0;" class>
            <div id="totalProgress" class="progress-bar progress-bar-success" style="width: 0%;"></div>
        </div>
    </div>

% else:

    <br />

% endif

<div id="grid">

    <div id="gitCrumb"></div>

    <div id="gitGrid"></div>


</div>

<script type="text/javascript">

    // Import JS variables
    // TODO: put these in contextVars namespace to avoid polluting global namespace,
     var branch = '${branch}',
        sha = '${sha}',
        canEdit = ${int(user['can_edit'])},
        hasAuth = ${int(has_auth)},
        hasAccess = ${int(has_access)},
        isHead = ${int(is_head)};
    // Namespace for variables grabbed from the python view through mako
    // These are accessible in any of the Github JS modules
    var contextVars = {
        // Node API URL
        apiUrl: "${api_url}",
        // Upload URL
        uploadUrl: "${upload_url}",
        // URL to get the hgrid root data
        hgridUrl: "${api_url + 'github/hgrid/'}",
        // SHA and branch,
        sha: "${sha}",
        branch: "${branch}"
    };

    // Submit branch form on change
    % if len(branches) > 1:
        $('#gitBranchSelect').on('change', function() {
            $(this).closest('form').submit();
        });
    % endif

</script>
