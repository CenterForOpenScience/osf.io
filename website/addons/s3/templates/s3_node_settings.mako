
<form role="form" id="addonSettings${addon_short_name.capitalize()}" data-addon="${addon_short_name}">

    <div>
        <h4 class="addon-title">
            Amazon S3

            <small class="authorized-by">
                % if node_has_auth:
                    authorized by
                    <a href="${owner_url}" target="_blank">
                        ${owner}
                    </a>
                    % if not is_registration:
                        <a id="s3RemoveToken" class="text-danger pull-right addon-auth">Deauthorize</a>
                    % endif
                % elif user_has_auth:
                    <a id="s3ImportToken" class="text-primary pull-right addon-auth">Import Credentials</a>
                % endif
            </small>

        </h4>
    </div>

    % if bucket_list is not None:

        <div class="form-group">

            <p> <strong>Current Bucket:</strong></p>

            <div class="row">

                <div class="col-md-6">

                    <select class="form-control" id="s3_bucket" name="s3_bucket"
                        ${'' if user_has_auth and user_is_owner and not is_registration else 'disabled'}>
                        <option value="">-----</option>
                        % for bucket_name in bucket_list or []:
                            <option value="${bucket_name}" ${'selected' if bucket_name == bucket else ''}>
                                ${bucket_name}
                            </option>
                        % endfor
                    </select>

                </div>

                % if user_has_auth and user_is_owner and not is_registration:
                    <div class="col-md-6">
                        <a class="btn btn-default" id="newBucket">Create Bucket</a>

                        <button class="btn btn-primary addon-settings-submit pull-right">
                            Submit
                        </button>
                    </div>
                % endif

            </div>

        </div> <!-- End form group -->

    % elif node_has_auth and bucket_list is None:

        <div>
            <span class="text-danger">
                Error loading S3 access keys. Please refresh the page.
            </span>
        </div>

    % elif not node_has_auth and not user_has_auth:

        <div class="form-group">
            <label for="s3Addon">Access Key</label>
            <input class="form-control" id="access_key" name="access_key"/>
        </div>
        <div class="form-group">
            <label for="s3Addon">Secret Key</label>
            <input type="password" class="form-control" id="secret_key" name="secret_key"/>
        </div>

        <button class="btn btn-success addon-settings-submit">
            Submit
        </button>
    % endif

    ${self.on_submit()}

    <div class="addon-settings-message" style="display: none; padding-top: 10px;"></div>

</form>

<%def name="on_submit()">
    <% import json %>
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars,
        {
            'currentUser': {
                'hasAuth': ${json.dumps(user_has_auth)}
            },
            's3SettingsSelector': '#addonSettings${addon_short_name.capitalize()}'

        });
    </script>
</%def>

