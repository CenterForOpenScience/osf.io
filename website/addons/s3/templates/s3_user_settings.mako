<%inherit file="project/addon/user_settings.mako" />

<div class="form-group">
    <label for="s3Addon">Access Key</label>
    <input class="form-control" id="access_key" name="access_key" value="${access_key}" ${'disabled' if disabled else ''} />
</div>
<div class="form-group">
    <label for="s3Addon">Secret Key</label>
    <input type="password" class="form-control" id="secret_key" name="secret_key" value="${secret_key}" ${'disabled' if disabled else ''} />
</div>

<%def name="submit_btn()">
 	%if has_auth:
        <button id="removeAccess" class="btn btn-danger">
            Remove Access
        </button>
    %else:
	    <button class="btn btn-success addon-settings-submit">
	        Submit
	    </button>
	%endif
</%def>
##TODO create a remove access key
##Update button? maybe?

<%def name="on_submit()">
    %if has_auth:
        <script type="text/javascript">
         $(document).ready(function() {
            $('#${addon_short_name}').on('submit', function() {
                var $this = $(this),
                addon = $this.attr('data-addon'),
                msgElm = $this.find('.addon-settings-message');
                $.ajax({
                    url: nodeApiUrl + '${addon_short_name}' + '/settings/delete/' + force,
                    type: 'POST',
                    contentType: 'application/json',
                    dataType: 'json',
                }).success(function() {
                    msgElm.text('Access key removed')
                        .removeClass('text-danger').addClass('text-success')
                        .fadeOut(100).fadeIn();
                }).fail(function(xhr) {
                    var message = 'Error: Access key not removed';
                    msgElm.text(message)
                        .removeClass('text-success').addClass('text-danger')
                        .fadeOut(100).fadeIn();
                });
                return false;
            });
        });
        </script>
    %else:
        ${parent.on_submit()}
    %endif
</%def>
