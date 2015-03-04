<%inherit file="base.mako"/>
<%def name="title()">Reset Password</%def>
<%def name="content()">
<h1 class="page-header text-center">Reset Password</h1>
<div class="row">
    <div class="col-md-6 col-md-offset-3">
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/reset_password/",
                "kwargs": {
                    "name": "resetpassword",
                    "id": "resetPasswordForm",
                    "method_string": "POST",
                    "action_string": "/resetpassword/${verification_key}/",
                    "form_class": "form-stacked",
                    "submit_string": "Reset Password"
                },
                "replace": true
            }'>
        </div>
    </div>
    <div class="col-md-4">&nbsp;</div>
</div>
</%def>
