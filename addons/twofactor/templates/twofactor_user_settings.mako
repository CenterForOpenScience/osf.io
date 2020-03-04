<div id="twoFactorScope" class="scripted">
  <h4 class="addon-title">
    ${_("Two-factor Authentication")}
      <small>
          <span data-bind="if: isEnabled">
            <a data-bind="click: disableTwofactor" class="text-danger pull-right addon-auth">
              ${_("Disable Two-Factor Authentication")}
            </a>
          </span>
          <span data-bind="ifnot: isEnabled">
            <a data-bind="click: enableTwofactor" class="text-primary pull-right addon-auth">
              ${_("Enable Two-Factor Authentication")}
            </a>
          </span>
      </small>
  </h4>

  <div id="TfaVerify" data-bind="visible: !isConfirmed()">
    <p>${_("By using two-factor authentication, you'll protect your GakuNin RDM account with both your password and your mobile phone.")}</p>
    <div data-bind="visible: isEnabled">
      <div class="alert alert-danger">
        <p><strong>${_("Important: ")}</strong>${_(" If you lose access to your mobile device, you will not be able to log in to your GakuNin RDM account.")}</p>
      </div>
      <p>${_('To use, you must install an appropriate application on your mobile device. Google Authenticator is a popular choice and is available for both\
        <a %(google_url)s>Android</a> and <a %(itunes_url)s>iOS</a>.') % dict(google_url='href="https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2"',itunes_url='href="https://itunes.apple.com/us/app/google-authenticator/id388497605?mt=8"') | n}</p>
      <p>${_("Once verified, your device will display a six-digit code that must be entered during the login process. This code changes every few seconds, which means that unauthorized users will not be able to log in to you account, <em>even if they know your password</em>.")}</p>
      <p>
        ${_('Scan the image below, or enter the secret key\
        %(secret_key)s into your authentication device.') % dict(secret_key='<code data-bind="text: secret"></code>') | n}
      </p>
      <div id="twoFactorQrCode"></div>
      <form data-bind="submit: submitSettings" class="form">
        <div class="form-group">
          <label class="control-label" for="TfaCode">${_("Enter your verification code:")}</label>
          <div>
            <input data-bind="value: tfaCode" type="text" name='TfaCode' id="TfaCode" class="form-control" />
            <input type="submit" value="Submit" class="btn btn-primary">
          </div>
          <div class="help-block">
            <p data-bind="html: message, attr: {class: messageClass}"></p>
          </div>
        </div>
      </form>
    </div>
  </div>
</div>
