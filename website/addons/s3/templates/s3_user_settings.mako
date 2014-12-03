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

        $('#s3RemoveAccess').on('click', function() {
            bootbox.confirm({
                title: 'Remove access key?',
                message: 'Are you sure you want to remove your Amazon Simple Storage Service access key? ' +
                        'This will revoke access to Amazon S3 for all projects you have authorized and ' +
                        'delete your access token from Amazon S3. Your OSF collaborators will not be able ' +
                        'to write to Amazon S3 buckets or view private buckets that you have authorized.',
                callback: function(result) {
                    if(result) {
                        deleteToken();
                    }
                }
            });
        });

        function deleteToken() {
            var $this = $(this),
            addon = $this.attr('data-addon'),
            msgElm = $this.find('.addon-settings-message');
            $.ajax({
                type: 'DELETE',
                url: '/api/v1/settings/s3/',
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    msgElm.text('Keys removed')
                        .removeClass('text-danger').addClass('text-success')
                        .fadeOut(100).fadeIn();
                    window.location.reload();
                },
                error: function(xhr) {
                    var response = JSON.parse(xhr.responseText);
                    if (response && response.message) {
                        if(response.message === 'reload')
                            window.location.reload();
                        else
                            message = response.message;
                    } else {
                        message = 'Error: Keys not removed';
                    }
                    msgElm.text(message)
                        .removeClass('text-success').addClass('text-danger')
                        .fadeOut(100).fadeIn();
                }
            });
            return false;
        }

        $(document).ready(function() {
            $('#addonSettings${addon_short_name.capitalize()}').on('submit', AddonHelper.onSubmitSettings);
        });

    </script>
</%def>

<%include file="profile/addon_permissions.mako" />
