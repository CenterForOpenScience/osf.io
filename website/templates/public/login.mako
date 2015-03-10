<%inherit file="base.mako"/>

<%def name="title()">Sign up or Log in</%def>

<%def name="content()">
    <div class="row">
        <div class="col-sm-4 col-sm-offset-4" data-bind="with: LogInForm">
            <h2>Sign-In</h2>
            <form
                    id="logInForm"
                    class="form-stacked"
                    data-bind="submit: submit"
                    % if next_url:
                        action="${ web_url_for('auth_login') }?next=${ next_url }"
                    % else:
                        action="${ web_url_for('auth_login') }"
                    % endif
                    method="POST"
                    >
                <fieldset>
                    <div class="form-group">
                        <label for="username">Email Address</label>
                        <span class="help-block"></span>
                        <input type="text" class="form-control" data-bind="value: username" name="username" placeholder="Username" autofocus>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <span class="help-block"></span>
                        <input type="password" class="form-control" data-bind="value: password" name="password" placeholder="Password">
                    </div>
                    <div>
                      <button type="submit" class="btn btn-submit btn-primary m-r-sm">Sign In</button>
                      <a href="${web_url_for('_forgot_password')}">Forgot Password?</a>
                    </div>
                </fieldset>
            </form>
        </div>
    </div>
</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/login-page.js" | webpack_asset}></script>
</%def>