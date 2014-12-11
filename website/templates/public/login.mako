<%inherit file="base.mako"/>

<%def name="title()">Sign up or Log in</%def>

<%def name="content()">
    <div class="row">
        <div class="col-sm-12">
            <div class="page-header">
                <h1>Create an Account or Sign-In</h1>
            </div>
        </div>
    </div>
    <div class="row">
        <div class="col-sm-5">
            <h2>Create Account</h2>
            <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/registration/",
                "kwargs": {
                    "id": "registerForm",
                    "name": "registration",
                    "method_string": "POST",
                    "action_string": "/register/",
                    "form_class": "form-stacked",
                    "submit_string": "Create Account",
                    "field_name_prefix": "register_",
                    "submit_btn_class": "btn-success",
                    "next_url": "${next}"
                },
                "replace": true
            }'></div>
        </div>
        <div class="col-sm-5 col-sm-offset-2">
            <h2>Sign-In</h2>
            <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/signin/",
                "kwargs": {
                    "id": "signinForm",
                    "name": "signin",
                    "method_string": "POST",
                    "action_string": "/login/?next=${next}",
                    "form_class": "form-stacked",
                    "submit_string": "Sign In",
                    "submit_btn_class": "btn-primary",
                    "next_url": "${next}"
                },
                "replace": true
            }'></div>
            <hr />
            <h3>Forgot Password</h3>
            <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/forgot_password/",
                "kwargs": {
                    "id": "forgotPassword",
                    "name": "forgotpassword",
                    "method_string": "POST",
                    "action_string": "/forgotpassword/",
                    "form_class": "form-stacked",
                    "submit_string": "Reset Password",
                    "submit_btn_class": "btn-default"
                },
                "replace": true
            }'></div>
        </div>
    </div>
    <div class="modal fade" id="twoFactor">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h4 style="margin-bottom:0">Two-factor Authentication</h4>
                </div>
                <div class="modal-body">
                    <p>Two-factor authentication helps protect your OSF account by requiring both a password and a code generated on your mobile phone to log in. This addon may be enabled on your account's <a href="${ web_url_for('user_addons') }">addon settings</a>.</p>
                    <p>If you have enabled two-factor authentication on your account, enter the current verification code from your device in this field.</p>
                </div>
                <div class="modal-footer">

                    <a href="#" class="btn btn-default" data-dismiss="modal">OK</a>
                </div>
            </div>
        </div>
    </div>
    <script>
        $(function() {
            $('#twoFactorHelpText').wrap('<a data-toggle="modal" href="#twoFactor">');
        });
    </script>
</%def>

