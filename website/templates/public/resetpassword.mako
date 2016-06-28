<%inherit file="base.mako"/>
<%def name="title()">Reset Password</%def>
<%def name="content()">
<h1 class="page-header text-center">Reset Password</h1>

<div>
    <div class="row">
        <form class="form col-md-8 col-md-offset-2 m-t-xl"
                id="resetPasswordForm"
                name="resetPasswordForm"
                method="POST"
                action="/resetpassword/${verification_key}/"
                >

            <div class="help-block" >
                <p data-bind="html: flashMessage, attr: {class: flashMessageClass}"></p>
            </div>
        <div class="row">
            <div
                class="form-group"
                data-bind="
                    css: {
                        'has-error': password() && !password.isValid(),
                        'has-success': password() && password.isValid()
                    }"
            >
                <label for="resetPassword" class="col-sm-4 control-label">New Password</label>
                <div class="col-sm-8">
                    <input
                        type="password"
                        class="form-control"
                        id="resetPassword"
                        name="password"
                        placeholder="Password"
                        data-bind="
                            textInput: typedPassword,
                            value: password,
                            event: {
                                blur: trim.bind($data, password)
                            }"
                    >
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
                </div>
            </div>
        </div>
        <div class="row">
            <div
                class="form-group"
                data-bind="
                    css: {
                        'has-error': passwordConfirmation() && !passwordConfirmation.isValid(),
                        'has-success': passwordConfirmation() && passwordConfirmation.isValid()
                    }"
            >
                <label for="resetPasswordConfirmation" class="col-sm-4 control-label">Verify New Password</label>
                <div class="col-sm-8">
                    <input
                        type="password"
                        class="form-control"
                        id="resetPasswordConfirmation"
                        name="password2"
                        placeholder="Verify Password"
                        data-bind="
                            value: passwordConfirmation,
                            event: {
                                blur: trim.bind($data, passwordConfirmation)
                            }"
                    >
                    <p class="help-block" data-bind="validationMessage: passwordConfirmation" style="display: none;"></p>
                </div>
            </div>
        </div>
        <button type="submit" class="btn btn-primary pull-right m-t-md" data-bind="css: {disabled: !password.isValid()}">Reset password</button>
        </form>
    </div>
</div>


</%def>

<%def name="javascript_bottom()">
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            verification_key: ${verification_key | sjson, n}
        });
    </script>
    ${parent.javascript_bottom()}
    <script src=${"/static/public/js/resetpassword-page.js" | webpack_asset}></script>
</%def>
