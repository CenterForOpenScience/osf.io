<%inherit file="base.mako"/>
<%def name="title()">Claim Account</%def>
<%def name="content()">
<h1 class="page-header text-center">Set Password</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
    <p>Hello ${ firstname }! Please set a password to claim your account.</p>
    <p>E-mail: <strong>${ email }</strong></p>

        <form class="form"
              id='setPasswordForm'
              name="setPasswordForm"
              method="POST"
        >
            <div
                class="form-group"
                data-bind="
                    css: {
                        'has-error': password() && !password.isValid(),
                        'has-success': password() && password.isValid()
                    }"
                style="margin-bottom: 5px"
            >
                <div>
                    <input
                        type="password"
                        class="form-control"
                        id="setPassword"
                        placeholder="Password"
                        name="password"
                        data-bind="
                            textInput: typedPassword,
                            value: password,
                            event: {
                                blur: trim.bind($data, password)
                            }"
                    >
                </div>
            </div>
            <div class="row" data-bind="visible: typedPassword().length > 0">
                <div class="col-xs-8">
                    <div class="progress create-password">
                        <div class="progress-bar progress-bar-sm" role="progressbar" data-bind="attr: passwordComplexityInfo().attr"></div>
                    </div>
                </div>
                <div class="col-xs-4 f-w-xl">
                    <!-- ko if: passwordFeedback() -->
                    <p id="front-password-info" data-bind="text: passwordComplexityInfo().text, attr: passwordComplexityInfo().text_attr"></p>
                    <!-- /ko -->
                </div>
            </div>

            <div>
                <!-- ko if: passwordFeedback() -->
                <p class="help-block osf-box-lt p-xs" data-bind="validationMessage: password" style="display: none;"></p>
                <p class="osf-box-lt " data-bind="css : { 'p-xs': passwordFeedback().warning }, visible: typedPassword().length > 0, text: passwordFeedback().warning"></p>
                <!-- /ko -->
            </div>




            <div
                class="form-group"
                data-bind="
                    css: {
                        'has-error': passwordConfirmation() && !passwordConfirmation.isValid(),
                        'has-success': passwordConfirmation() && passwordConfirmation.isValid()
                    }"
            >
                <div>
                    <input
                        type="password"
                        class="form-control"
                        id="setPasswordConfirmation"
                        placeholder="Verify Password"
                        name="password2"
                        data-bind="
                            value: passwordConfirmation,
                            event: {
                                blur: trim.bind($data, passwordConfirmation)
                            }"
                    >
                    <p class="help-block" data-bind="validationMessage: passwordConfirmation" style="display: none;"></p>
                </div>
            </div>

            <!-- Terms of Service and Privacy Policy agreement -->
            <div class="form-group">
                    <input type="checkbox" data-bind="checked: acceptedTermsOfService" name="accepted_terms_of_service">
                    <label style="margin-right: 15px">I have read and agree to the <a href="https://github.com/CenterForOpenScience/cos.io/blob/master/TERMS_OF_USE.md">Terms of Use</a> and <a href="https://github.com/CenterForOpenScience/cos.io/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>.</label>
                    <p class="help-block" data-bind="validationMessage: acceptedTermsOfService" style="display: none;"></p>
            </div>

            %if recaptcha_site_key:
                <div class="row">
                    <div class="col-sm-12">
                        <div class="pull-right p-b-sm g-recaptcha" data-sitekey="${recaptcha_site_key}"></div>
                    </div>
                </div>
            %endif
            <div class='help-block'>
                <p>If you are not ${fullname}, or if you were erroneously added as a contributor to the project described in the email invitation, please email <a href="mailto:${osf_contact_email}">${osf_contact_email}</a>
                </p>
            </div>
            ${form.token | unicode, n }
            %if next_url:
                <input type='hidden' name='next_url' value='${next_url}'>
            %endif
            <button type='submit' class="btn btn-success pull-right" data-bind="disable: !acceptedTermsOfService()">Save</button>
        </form>
    </div>
</div>

</%def>

<%def name="javascript_bottom()">
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            username: ${email | sjson, n}
        });
    </script>
    ${parent.javascript_bottom()}
    <script src=${"/static/public/js/claimaccount-page.js" | webpack_asset}></script>
    %if recaptcha_site_key:
        <script src="https://recaptcha.net/recaptcha/api.js" async defer></script>
    %endif
</%def>
