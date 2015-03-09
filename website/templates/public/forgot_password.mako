<%inherit file="base.mako"/>

<%def name="title()">Forgot Password</%def>

<%def name="content()">
    ## TODO refactor base.mako to inherit from another, higher level
    ## template with just the assets to avoid this css magic /hrybacki
    <style>
          .footer, .copyright, .osf-nav-wrapper  {
            display: none;
          }
    </style>

    <form class="form col-md-4 col-md-offset-4"
            id="forgotPasswordForm"
            class="form"
            % if next_url:
                action="/forgotpassword/?next=${next_url}"
            % else:
                action="/forgotpassword/"
            % endif
            method="POST"
            data-bind="submit: submit"
        >
        <div class="panel panel-primary">
            <div class="panel-heading">Password Reset Request</div>
                <div class="panel-body">
                    <input type="email" class="form-control" data-bind="value: username" name="forgot_password-email" placeholder="Enter your email address" autofocus/>
                    <button type="submit" class="btn btn-success pull-right m-t-md">Reset Password</button>
                </div>
        </div>
        <hr class="m-t-lg m-b-sm"/>
        <h6 class="text-center text-muted text-300"><a href="${ web_url_for('auth_login') }">Back to OSF</a></h6>
    </form>

</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/forgotpassword-page.js" | webpack_asset}></script>
</%def>