<%inherit file="base.mako"/>

<%def name="title()">Forgot Password</%def>

<%def name="content()">

    <div class="row">
        <form class="form col-md-4 col-md-offset-4 m-t-xl"
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
            <div class="panel panel-osf">
                <div class="panel-heading">Password reset request</div>
                    <div class="panel-body">
                        <input type="email" class="form-control" data-bind="value: username" name="forgot_password-email" placeholder="Enter your email address" autofocus/>
                        <button type="submit" class="btn btn-primary pull-right m-t-md">Reset password</button>
                    </div>
            </div>
            <hr class="m-t-lg m-b-sm"/>
            <h6 class="text-center text-muted text-300"><a href="${ web_url_for('index') }">Back to OSF</a></h6>
        </form>
    </div>

</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/forgotpassword-page.js" | webpack_asset}></script>
</%def>