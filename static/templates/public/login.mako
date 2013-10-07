<%inherit file="contentContainer.mako" />

<div class="page-header">
    <h1>Create an Account or Sign-In</h1>
</div>

<div class="row">
    <div class="span1">&nbsp;</div>
    <div class="span6">
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
                    "field_name_prefix": "register_"
                },
                "replace": true
            }'>
        </div>

    </div>
    <div class="span4">
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
                    "submit_string": "Sign In"
                },
                "replace": true
            }'>
        </div>
        <hr />
        <h3>Forgot Password</h3>
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/forgot_password/",
                "kwargs": {
                    "name": "forgotpassword",
                    "method_string": "POST",
                    "action_string": "/forgotpassword/",
                    "form_class": "form-stacked",
                    "submit_string": "Reset Password"
                },
                "replace": true
            }'>
        </div>
    </div>
    <div class="span1">&nbsp;</div>
</div>
