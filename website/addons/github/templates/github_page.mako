<%inherit file="project/addon/page.mako" />

<%def name="page()">

% if not gh_user:

    <div mod-meta='{
            "tpl": "project/addon/config_error.mako",
            "kwargs": {
                "short_name": "${short_name}",
                "full_name": "${full_name}"
            }
        }'></div>

% else:

    <div class="row">

        <div class="col-md-6">

            <h4>
                Viewing ${gh_user} / ${repo}
                % if show_commit_id:
                    : ${commit_id}
                % endif
            </h4>

            % if len(branches) == 1:

                ${branches[0]['name']}

            % elif len(branches) > 1:

                <form role="form">
                    <select id="gitBranchSelect" name="branch">
                        % for branch in branches:
                            <option
                                value=${branch['name']}
                                ${'selected' if commit_id in [branch['name'], branch['commit']['sha']] else ''}
                            >${branch['name']}</option>
                        % endfor
                    </select>
                </form>

            % endif

        </div>

        <div class="col-md-6">

            <h4>Download:</h4>

            <p><a href="${api_url}github/tarball/">Tarball</a></p>
            <p><a href="${api_url}github/zipball/">Zip</a></p>

        </div>

    </div>

    % if user['can_edit']:

        % if has_auth:

            <div class="container" style="position: relative;">
                <h3 id="dropZoneHeader">Drag and drop (or <a href="#" id="gitFormUpload">click here</a>) to upload files</h3>
                <div id="fallback"></div>
                <div id="totalProgressActive" style="width: 35%; height: 20px; position: absolute; top: 73px; right: 0;" class>
                    <div id="totalProgress" class="progress-bar progress-bar-success" style="width: 0%;"></div>
                </div>
            </div>

        % else:

            <p>
                This GitHub add-on has not been authenticated. To enable file uploads and deletion,
                browse to the <a href="${node['url']}settings/">settings</a> page and authenticate this add-on.
            <p>

        % endif

    % endif

    <div id="grid">
        <div id="gitCrumb"></div>
        <div id="gitGrid"></div>
    </div>

    <script type="text/javascript">

        // Import JS variables
        var gridData = ${grid_data},
            ref = '${commit_id}',
            canEdit = ${int(user['can_edit'])},
            hasAuth = ${int(has_auth)};

        // Submit branch form on change
        % if len(branches) > 1:
            $('#gitBranchSelect').on('change', function() {
                $(this).closest('form').submit();
            });
        % endif

    </script>

    % endif

</%def>
