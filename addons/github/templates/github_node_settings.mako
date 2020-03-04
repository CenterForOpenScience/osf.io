<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}">

    <div>
        <h4 class="addon-title">
            <img class="addon-icon" src="${addon_icon_url}">
            GitHub
            <small class="authorized-by">
                % if node_has_auth:
                        authorized by
                        <a href="${auth_osf_url}" target="_blank">
                            ${auth_osf_name}
                        </a>
                    % if not is_registration:
                        <a id="githubRemoveToken" class="text-danger pull-right addon-auth" >
                          ${_("Disconnect Account")}
                        </a>
                    % endif
                % else:
                    % if user_has_auth:
                        <a id="githubImportToken" class="text-primary pull-right addon-auth">
                           ${_("Import Account from Profile")}
                        </a>
                    % else:
                        <a id="githubCreateToken" class="text-primary pull-right addon-auth">
                           ${_("Connect Account")}
                        </a>
                    % endif
                % endif
            </small>
        </h4>
    </div>

    % if node_has_auth and valid_credentials:

        <input type="hidden" id="githubUser" name="github_user" value="${github_user}" />
        <input type="hidden" id="githubRepo" name="github_repo" value="${github_repo}" />

        <p><strong>${_("Current Repo: ")}</strong>

        % if is_owner and not is_registration:
        </p>
        <div class="row">
            <div class="col-md-6 m-b-sm">
                <select id="githubSelectRepo" class="form-control" ${'disabled' if not is_owner or is_registration else ''}>
                    <option>-----</option>
                    % for repo_name in repo_names:
                        <option value="${repo_name['path']}" ${'selected' if repo_name['path'] == github_repo_full_name else ''}>${repo_name['path']}</option>
                    % endfor
                </select>
            </div>

            <div class="col-md-6 m-b-sm">
                <button class="btn btn-success addon-settings-submit">
                    ${_("Save")}
                </button>
                <a id="githubCreateRepo" class="btn btn-success pull-right">${_("Create Repo")}</a>
            </div>
        </div>
        % elif github_repo_full_name:
            <a href="${files_url}">${github_repo_full_name}</a></p>
        % else:
            <span>${_("None")}</span></p>
        % endif
    % endif

    ${self.on_submit()}

    % if node_has_auth and not valid_credentials:
        <div class="addon-settings-message text-danger p-t-sm">
            % if is_owner:
                ${_('Could not retrieve %(addonName)s settings at this time. The %(addonName)s addon credentials\
                may no longer be valid. Try deauthorizing and reauthorizing %(addonName)s on your\
                <a href="%(addons_url)s">account settings page</a>.') % dict(addons_url=h(addons_url),addonName='GitHub') | n}
            % else:
                ${_("Could not retrieve %(addonName)s settings at this time. The %(addonName)s addon credentials\
                may no longer be valid. Contact %(auth_osf_name)s to verify.") % dict(auth_osf_name=auth_osf_name,addonName='GitHub')}
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
            'githubSettingsSelector': '#addonSettings${addon_short_name.capitalize()}'
        });
    </script>
</%def>
