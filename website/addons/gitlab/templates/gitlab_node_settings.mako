<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}">

    <div>
        <h4 class="addon-title">
            <img class="addon-icon" src="${addon_icon_url}">
            GitLab
            <small class="authorized-by">
                % if node_has_auth:
                        authorized by
                        <a href="${auth_osf_url}" target="_blank">
                            ${auth_osf_name}
                        </a>
                    % if not is_registration:
                        <a id="gitlabRemoveToken" class="text-danger pull-right addon-auth" >
                          Disconnect Account
                        </a>
                    % endif
                % else:
                    % if user_has_auth:
                        <a id="gitlabImportToken" class="text-primary pull-right addon-auth">
                           Import Account from Profile
                        </a>
                    % else:
                        <a id="gitlabCreateToken" class="text-primary pull-right addon-auth">
                           Connect Account
                        </a>
                    % endif
                % endif
            </small>
        </h4>
    </div>

    % if node_has_auth and valid_credentials:

        <input type="hidden" id="gitlabUser" name="gitlab_user" value="${gitlab_user}" />
        <input type="hidden" id="gitlabRepo" name="gitlab_repo" value="${gitlab_repo}" />

        <p><strong>Current Repo: </strong>

        % if is_owner and not is_registration:
        </p>
        <div class="row">
            <div class="col-md-6 m-b-sm">
                <select id="gitlabSelectRepo" class="form-control" ${'disabled' if not is_owner or is_registration else ''}>
                    <option>-----</option>
                        % if is_owner:
                            % for repo_name in repo_names:
                                <option value="${repo_name}" ${'selected' if repo_name == gitlab_repo_full_name else ''}>${repo_name}</option>
                            % endfor
                        % else:
                            <option selected>${gitlab_repo_full_name}</option>
                        % endif
                </select>
            </div>

            <div class="col-md-6 m-b-sm">
                <button class="btn btn-success addon-settings-submit">
                    Save
                </button>
                <a id="gitlabCreateRepo" class="btn btn-success pull-right">Create Repo</a>
            </div>
        </div>
        % elif gitlab_repo_full_name:
            <a href="${files_url}">${gitlab_repo_full_name}</a></p>
        % else:
            <span>None</span></p>
        % endif
    % endif

    ${self.on_submit()}

    % if node_has_auth and not valid_credentials:
        <div class="addon-settings-message text-danger p-t-sm">
            % if is_owner:
                Could not retrieve GitLab settings at this time. The GitLab addon credentials
                may no longer be valid. Try deauthorizing and reauthorizing GitLab on your
                <a href="${addons_url}">account settings page</a>.
            % else:
                Could not retrieve GitLab settings at this time. The GitLab addon credentials
                may no longer be valid. Contact ${auth_osf_name} to verify.
            % endif
        </div>
    % else:
        <div class="addon-settings-message p-t-sm" style="display: none"></div>
    % endif

</form>

<%def name="on_submit()">
    <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {
            ## Short name never changes
            'gitlabSettingsSelector': '#addonSettings${addon_short_name.capitalize()}'
        });
    </script>
</%def>
