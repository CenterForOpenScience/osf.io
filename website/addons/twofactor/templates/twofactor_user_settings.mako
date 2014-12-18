

## TODO: Load this as a dependency of twoFactoryUserConfig module w/ script.js
<script type="text/javascript" src="/static/addons/twofactor/jquery.qrcode.min.js"></script>

<h4 class="addon-title">Two-factor Authentication</h4>

% if not is_confirmed:
<style>
    #TfaCode {
        width:6em;
        display:inline;
        margin-right:5px;
        padding-top: 4px;
    }
</style>
<div id="twoFactorScope" class="scripted">
    <div id="TfaVerify" class="addon-settings">
        <p>By using two-factor authentication, you'll protect your OSF account with both
            your password and your mobile phone.</p>
        <div class="alert alert-danger"><p><strong>Important: </strong> If you lose access to your mobile device, you will not be able to log in to your OSF account.</p></div>
        <p>To use, you must install an appropriate application on your mobile device. Google Authenticator
            is a popular choice and is available for both
            <a href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2">Android</a>
            and <a href="https://itunes.apple.com/us/app/google-authenticator/id388497605?mt=8">iOS</a>.</p>
        <p>Once verified, your device will display a six-digit code that must be entered during the
            login process. This code changes every few seconds, which means that unauthorized users
            will not be able to log in to you account, <em>even if they know your password</em>.</p>
        <p>Scan the image below, or enter the secret key <code>${ secret }</code> into your authentication device.</p>
        <div id="twoFactorQrCode"></div>

        <form data-bind="submit: submitSettings" class="form">
            <div class="form-group">
                <label class="control-label" for="TfaCode">Enter your verification code:</label>
                <div>
                    <input data-bind="value: tfaCode" type="text" name='TfaCode' id="TfaCode" class="form-control" />
                    <input type="submit" value="Submit" class="btn btn-primary">
                </div>
                <div class="help-block">
                    <p data-bind="html: message, attr.class: messageClass"></p>
                </div>
            </div>
        </form>

    </div>
</div>
% endif
<div id="TfaDeactivate" ${ 'style="display:none"' if not is_confirmed else ''}>
    <p class="text-success">Enabled</p>
</div>

<script>
    window.contextVars = window.contextVars || {};
    window.contextVars.otpauthURL = "${otpauth_url}";
</script>
