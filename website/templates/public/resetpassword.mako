<%inherit file="base.mako"/>
<%def name="title()">Reset Password</%def>
<%def name="content()">
<h1 class="page-header text-center">Reset Password</h1>

<div>
    <div class="row">
        <form class="form col-md-8 col-md-offset-2 m-t-xl"
                id="resetPasswordForm"
                class="form"
                method="POST"
                action="/resetpassword/${verification_key}"
                data-bind="submit: submit"
            >

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
                        placeholder="Password"
                        data-bind="
                            textInput: typedPassword,
                            value: password,
                            disable: submitted(),
                            event: {
                                blur: trim.bind($data, password)
                            }"
                    >
                    <p class="help-block" data-bind="validationMessage: password" style="display: none;"></p>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="form-group">
                <label class="col-sm-4 control-label">Strength</label>
                <div class="col-sm-8">
                    <div class="progress create-password">
                        <div class="progress-bar progress-bar-success" role="progressbar" data-bind="attr: passwordComplexityBar"></div>
                    </div>
                    <p class="help-block" data-bind="text: passwordFeedback"></p>
                </div>
            </div>
        </div>
        <div class="row">
            <div
                class="form-group"
                data-bind="
                    css: {
                        'has-error': password_confirmation() && !password_confirmation.isValid(),
                        'has-success': password_confirmation() && password_confirmation.isValid()
                    }"
            >
                <label for="resetPasswordConfirmation" class="col-sm-4 control-label">Verify New Password</label>
                <div class="col-sm-8">
                    <input
                        type="password"
                        class="form-control"
                        id="resetPasswordConfirmation"
                        placeholder="Verify Password"
                        data-bind="
                            value: password_confirmation,
                            disable: submitted(),
                            event: {
                                blur: trim.bind($data, password_confirmation)
                            }"
                    >
                    <p class="help-block" data-bind="validationMessage: password_confirmation" style="display: none;"></p>
                </div>
            </div>
        </div>

            <!-- Flashed Messages -->
            <div class="help-block" >
                <p data-bind="html: flashMessage, attr: {class: flashMessageClass}"></p>
            </div>
            <button type="submit" class="btn btn-primary pull-right m-t-md">Reset password</button>
        </form>
    </div>
</div>


</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src=${"/static/public/js/resetpassword-page.js" | webpack_asset}></script>
</%def>
