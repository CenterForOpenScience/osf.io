<%inherit file="base.mako"/>

<%def name="title()">
  % if institutional:
    Reset Institutional Password
  % else:
    Forgot Password
  % endif
</%def>

<%def name="content()">

  % if institutional:
    <div class="row">
      <div class="panel-heading"></div>
      <div class="panel-body">
        % if isError:
          <p class="alert alert-danger">${message}</p>
        % else:
          <p class="alert alert-success">${message}</p>
        % endif
      </div>
    </div>
  % else:
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
  % endif

</%def>

<%def name="javascript_bottom()">
  % if not institutional:
    <script src=${"/static/public/js/forgotpassword-page.js" | webpack_asset}></script>
  % endif
</%def>
