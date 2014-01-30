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
##TODO Clear key fields
<%def name="on_submit()">
    %if has_auth:
        <script type="text/javascript">
         $(document).ready(function() {
            $('#addonSettings${addon_short_name.capitalize()}').on('submit', function() {
                var $this = $(this),
                addon = $this.attr('data-addon'),
                msgElm = $this.find('.addon-settings-message');
                $.ajax({
                    url: '/api/v1/settings/s3/delete/',
                    type: 'POST',
                    contentType: 'application/json',
                    dataType: 'json',
                }).success(function() {
                    $('#access_key').val('');
                    $('#secret_key').val('');
                    msgElm.text('Keys removed')
                        .removeClass('text-danger').addClass('text-success')
                        .fadeOut(100).fadeIn();
                }).fail(function(xhr) {
                    var message = 'Error: Keys not removed';
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


##TODO make this work nicely. Somehow
<%doc>
<script type="text/javascript">
     $(document).ready(function() {
        $('#access_key').on('keydown', function() {
            $('#removeAccess').attr('class', 'btn btn-primary addon-settings-submit');
            $('#removeAccess').text('Update');
            $('#${addon_short_name}').on('submit', on_submit_settings);
            $('#secret_key').off('keydown')
            $('#access_key').off('keydown')
        });
        $('#secret_key').on('keydown', function() {
            $('#removeAccess').attr('class', 'btn btn-primary addon-settings-submit');
            $('#removeAccess').text('Update');
            $('#${addon_short_name}').off('submit', on_submit_settings);
            $('#${addon_short_name}').submit(on_submit_settings);
            $('#secret_key').off('keydown')
            $('#access_key').off('keydown')
        });
    });
</script>
</%doc>
