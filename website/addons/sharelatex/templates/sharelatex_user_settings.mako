<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}">
    <span data-owner="user"></span>
    <div>
        <h4 class="addon-title">
          <img class="addon-icon" src="${addon_icon_url}"></img>
            ShareLatex

            <small class="authorized-by">
                % if has_auth:
                    authorized by <em>${name}</em>
                    <a id="sharelatexRemoveAccess" class="text-danger pull-right addon-auth">Disconnect Account</a>
                % endif
            </small>

        </h4>
    </div>

    % if not has_auth:
        <div class="form-group">
            <label for="sharelatexAddon">URL</label>
            <input class="form-control" id="sharelatex_url" name="sharelatex_url" ${'disabled' if disabled else ''} />
        </div>
        <div class="form-group">
            <label for="sharelatexAddon">Auth Token</label>
            <input type="password" class="form-control" id="auth_token" name="auth_token" ${'disabled' if disabled else ''} />
        </div>

        <button class="btn btn-success addon-settings-submit">
            Save
        </button>
    % endif

    ${self.on_submit()}

    <!-- Form feedback -->
    <div class="addon-settings-message" style="display: none; padding-top: 10px;"></div>

</form>

<%def name="on_submit()">
    <script type="text/javascript">
        window.contextVars = $.extend({}, window.contextVars, {'addonSettingsSelector': '#addonSettings${addon_short_name.capitalize()}'});
    </script>
</%def>

<%include file="profile/addon_permissions.mako" />
