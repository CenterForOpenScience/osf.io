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
              <div class="progress create-password">
                  <div class="progress-bar progress-bar-sm" role="progressbar" data-bind="attr: passwordComplexityInfo().attr"></div>
              </div>
              <div>
                  <!-- ko if: passwordFeedback() -->
                  <p class="text-right" id="front-password-info" data-bind="text: passwordComplexityInfo().text, attr: passwordComplexityInfo().text_attr"></p>
                  <p class="help-block osf-box-lt" data-bind="validationMessage: password" style="display: none;"></p>
                  <p class="help-block osf-box-lt" data-bind="text: passwordFeedback().warning"></p>
                  <!-- /ko -->
                  <!-- ko if: !passwordFeedback() -->
                  <div style="padding-top:20px"></div>
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
            <div class='help-block'>
                <p>If you are not ${fullname}, or if you were erroneously added as a contributor to the project described in the email invitation, please email <a href="mailto:contact@osf.io">contact@osf.io</a>
                </p>
                <p>By clicking "Save" and creating an account you agree to our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/TERMS_OF_USE.md">Terms</a> and that you have read our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>, including our information on <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md#f-cookies">Cookie Use</a>.</p>
            </div>
            ${form.token | unicode, n }
            ${form.email | unicode, n }
            %if next_url:
                <input type='hidden' name='next_url' value='${next_url}'>
            %endif
            <button type='submit' class="btn btn-success pull-right" data-bind="css: {disabled: !password.isValid()}">Save</button>
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
</%def>
