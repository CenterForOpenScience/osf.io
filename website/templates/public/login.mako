<%inherit file="minimal_base.mako"/>

<%def name="title()">Sign In</%def>

<%def name="content()">

    <form
            id="logInForm"
            class="form col-sm-4 col-sm-offset-4"
            % if next_url:
                action="${ web_url_for('auth_login') }?next=${ next_url }"
            % else:
                action="${ web_url_for('auth_login') }"
            % endif
            method="POST"
            data-bind="submit: submit"

        >
            <div class="panel panel-primary">
            <div class="panel-heading">Sign In</div>
                <div class="panel-body">
                    <label for="username">Email Address</label>
                    <input type="email" class="form-control" data-bind="value: username" name="username" placeholder="Enter your username" autofocus/>
                    <label class="m-t-md" for="password">Password</label>
                    <input type="password" class="form-control" data-bind="value: password" name="password" placeholder="Enter your password">

                    <fieldset class="pull-right">
                        <button type="submit" class="btn btn-success m-t-md">Sign In</button>

                    </fieldset>
                </div>
        </div>
        <hr class="m-t-lg m-b-sm"/>
        <h6 class="text-center text-muted text-300">
            <a href="${ web_url_for('index') }">Back to OSF</a>
            <a class="m-l-xl" href="${ web_url_for('_forgot_password') }">Forgot Your Password?</a>
        </h6>
    </form>

</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/login-page.js" | webpack_asset}></script>
</%def>