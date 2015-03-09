<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}">

    <span data-owner="user"></span>

    <div>
        <h4 class="addon-title">
            Amazon S3

            <small class="authorized-by">
                % if has_auth:
                    authorized
                    <a id="s3RemoveAccess" class="text-danger pull-right addon-auth">Delete Credentials</a>
                % endif
            </small>

        </h4>
    </div>

    % if not has_auth:
        <div class="form-group">
            <label for="s3Addon">Access Key</label>
            <input class="form-control" id="access_key" name="access_key" ${'disabled' if disabled else ''} />
        </div>
        <div class="form-group">
            <label for="s3Addon">Secret Key</label>
            <input type="password" class="form-control" id="secret_key" name="secret_key" ${'disabled' if disabled else ''} />
        </div>

        <button class="btn btn-success addon-settings-submit">
            Submit
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
