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
                    <p class="help-block" data-bind="validationMessage: password" style="display: none;"></p>
                </div>
            </div>
            <div class="progress create-password">
                <div class="progress-bar progress-bar-success" role="progressbar" data-bind="attr: passwordComplexityBar"></div>
            </div>
            <p class="help-block" data-bind="text: passwordFeedback"></p>
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
            %if next_url:
                <input type='hidden' name='next_url' value='${next_url}'>
            %endif
            <button type='submit' class="btn btn-success pull-right" data-bind="css: {disabled: !password.isValid()}">Save</button>
        </form>
    </div>
</div>

</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src=${"/static/public/js/claimaccount-page.js" | webpack_asset}></script>
</%def>
