<%inherit file="base.mako"/>
<%def name="title()">Reset Password</%def>
<%def name="content()">
<div class="page-header">
    <h1>Reset Password</h1>
</div>
<div class="row">
    <div class="span1">&nbsp;</div>
    <div class="span6">
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/reset_password/",
                "kwargs": {
                    "name": "resetpassword",
                    "method_string": "POST",
                    "action_string": "/resetpassword/${verification_key}/",
                    "form_class": "form-stacked",
                    "submit_string": "Reset Password"
                },
                "replace": true
            }'>
        </div>
    </div>
    <div class="span4">&nbsp;</div>
    <div class="span1">&nbsp;</div>
</div>
</%def>
