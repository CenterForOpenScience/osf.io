<%inherit file="project/addon/user_settings.mako" />

<script type="text/javascript" src="/static/addons/twofactor/jquery.qrcode.min.js"></script>

% if not is_confirmed:
<style>
    #TfaCode {
        width:6em;
        display:inline;
        margin-right:5px;
        padding-top: 4px;
    }
</style>
<div id="TfaVerify">
    <p>Two-factor authentication will help protect your OSF account by requiring access to your mobile device to log in.</p>
    <p>To use, you must install an appropriate application on your mobile device. Google Authenticator is a popular choice and is available for both <a href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2">Android</a> and <a href="https://itunes.apple.com/us/app/google-authenticator/id388497605?mt=8">iOS</a>.</p>
    <p>Once verified, your device will display a six-digit code that must be entered during the login process. This code changes every few seconds, which means that unauthorized users will not be able to log in to you account, <em>even if they know your password</em>.</p>
    <p>Scan the image below, or enter the secret key <code>${ secret }</code> into your authentication device.</p>
    <div id="twoFactorQrCode"></div>
    <div class="form-group"></div>
        <label class="control-label" for="TfaCode">Enter your verification code:</label>
        <div>
            <input type="text" name='TfaCode' id="TfaCode" class="form-control" />
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
            $.osf.postJSON(
                    '/api/v1/settings/twofactor/',
                    {code: $('#TfaCode').val()},
                    function(data) {
                        $('#TfaVerify').slideUp(function() {
                            $('#TfaDeactivate').slideDown();
                        });
                        settingsElm.find('.addon-settings-message')
                                .removeClass('text-danger')
                                .fadeOut(100)
                    },
                    function(e) {
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
            )
        })
    });
</script>
% endif
<div id="TfaDeactivate" ${ 'style="display:none"' if not is_confirmed else ''}>
    <p class="text-success">Enabled</p>
</div>



<%def name="on_submit()"></%def>
<%def name="submit_btn()"></%def>