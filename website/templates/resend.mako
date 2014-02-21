<%inherit file="base.mako"/>
<%def name="title()">Resend Confirmation Email</%def>
<%def name="content()">
<h1 class="page-header text-center">Resend Confirmation Email</h1>

<div class="row">
    ## Center the form
    <div class="col-md-6 col-md-offset-3">
        <p class='help'>Enter your email address and we'll resend your
        confirmation link.
        </p>
        <div mod-meta='{
                "tpl": "util/render_form.mako",
                "uri": "/resend/",
                "kwargs": {
                    "name": "resend_confirmation",
                    "method_string": "POST",
                    "action_string": "#",
                    "form_class": "form",
                    "submit_string": "Submit"
                },
                "replace": true
            }'>
        </div>
    </div>
</div>
</%def>
