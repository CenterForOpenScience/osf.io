<%inherit file="project/addon/user_settings.mako" />

<script type="text/javascript" src="/static/vendor/jquery-qrcode/jquery.qrcode.min.js"></script>

% if not is_confirmed:
<div id="TfaVerify">
    <p>Scan the image below, or enter the secret key <code>${ secret }</code> into your authentication device.</p>
    <div id="twoFactorQrCode"></div>
    <div class="form-group" style="margin-bottom:0;margin-top:10px;">
        <label class="control-label" for="TfaCode">Enter your verification code:</label>
        <div>
            <input type="text" name='TfaCode' id="TfaCode" class="form-control" style="width:6em;display:inline;margin-right:5px;"/>
            <button class="btn btn-primary" id="TfaSubmit">Submit</button>
        </div>
    </div>
</div>
<script>
    $(function() {
        // Generate QR code
        $('#twoFactorQrCode').qrcode("${ otpauth_url }")

        $('#TfaSubmit').on('click', function(e) {
            e.preventDefault();
            var settingsElm = $(e.target).parents('.addon-settings');
            $.ajax({
                url: '/api/v1/settings/twofactor/',
                type: 'POST',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify({code: $('#TfaCode').val()}),
                success: function(data) {
                    $('#TfaVerify').slideUp(complete = function() {
                        $('#TfaDeactivate').slideDown();
                    });
                    settingsElm.find('.addon-settings-message')
                            .removeClass('text-danger')
                            .fadeOut(100)
                },
                error: function(e) {
                    var msgElm = settingsElm.find('.addon-settings-message')
                        .removeClass('text-success')
                        .addClass('text-danger');

                    if (e.status == 403) {
                        msgElm.text('Verification failed');
                    } else {
                        msgElm.text('Unexpected HTTP Error (' + e.status + '/' + e.statusText + ')');
                    }
                    msgElm.fadeOut(100).fadeIn();
                }
            })
        })
    });
</script>
% endif
<div id="TfaDeactivate" ${ 'style="display:none"' if not is_confirmed else ''}>
    <p class="text-success">Enabled</p>
</div>



<%def name="on_submit()"></%def>
<%def name="submit_btn()"></%def>