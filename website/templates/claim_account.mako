<%inherit file="base.mako"/>
<%def name="title()">Claim Account</%def>
<%def name="content()">
<h1 class="page-header text-center">Set Password</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
    <p>Hello ${firstname}! Welcome to the Open Science Framework. Please set a password to claim your account.</p>

        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/api/v1/forms/set_email_and_password/",
                "kwargs": {
                    "name": "resetpassword",
                    "method_string": "POST",
                    "action_string": "#",
                    "form_class": "form",
                    "submit_string": "Submit"
                },
                "replace": true
            }'>
        </div>
        <div class='help-block'>

            <p>If you are not ${fullname}, please contact <a href="mailto:contact@centerforopenscience.org">contact__AT__centerforopenscience.org</a>
            </p>
        </div>
    </div>
</div>
</%def>

<%def name="javascript_bottom()">
<script>
## Prepopulate email address with the 'email' url param
(function($) {
    var emailVal = $.urlParam('email').trim()
    if (emailVal.length) {
        $('#username').val(emailVal);
    }
})(jQuery);
</script>
</%def>
