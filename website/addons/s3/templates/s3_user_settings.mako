<%inherit file="project/addon/user_settings.mako" />

% if not has_auth:
    <div class="form-group">
        <label for="s3Addon">Access Key</label>
        <input class="form-control" id="access_key" name="access_key" ${'disabled' if disabled else ''} />
    </div>
    <div class="form-group">
        <label for="s3Addon">Secret Key</label>
        <input type="password" class="form-control" id="secret_key" name="secret_key" ${'disabled' if disabled else ''} />
    </div>
% endif

<%def name="submit_btn()">
 	% if has_auth:
        <button id="removeAccess" class="btn btn-danger">
            Delete Access Keys
        </button>
    % else:
	    <button class="btn btn-success addon-settings-submit">
	        Submit
	    </button>
	% endif
</%def>

<%def name="on_submit()">
    %if has_auth:
        <script type="text/javascript">
         $(document).ready(function() {
            $('#addonSettings${addon_short_name.capitalize()}').on('submit', function() {
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
            });
        });
        </script>
    %else:
        ${parent.on_submit()}
    %endif
</%def>

<%include file="profile/addon_permissions.mako" />