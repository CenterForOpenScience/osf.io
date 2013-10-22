<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>


<div class="row">
    <div class="col-md-5">
        <h2>Create Account</h2>
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/registration/",
                "kwargs": {
                    "name": "registration",
                    "method_string": "POST",
                    "action_string": "/register/",
                    "form_class": "form-stacked",
                    "submit_string": "Create Account",
                    "field_name_prefix": "register_",
                    "submit_btn_class": "btn-success"
                },
                "replace": true
            }'>
        </div>
    </div>
    <div class="col-md-5 col-md-offset-2">
        <h2>Sign-In</h2>
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/signin/",
                "kwargs": {
                    "id": "signinForm",
                    "name": "signin",
                    "method_string": "POST",
                    "action_string": "/login/",
                    "form_class": "form-stacked",
                    "submit_string": "Sign In",
                    "submit_btn_class": "btn-primary"
                },
                "replace": true
            }'></div>

        <hr />

        <h3>Forgot Password</h3>
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/forgot_password/",
                "kwargs": {
                    "id": "forgotpassword",
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
    <div class="col-md-1">&nbsp;</div>

</div>

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>
