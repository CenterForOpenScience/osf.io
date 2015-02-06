<%inherit file="base.mako"/>

<%def name="title()">Two Factor Authentication</%def>

<%def name="content()">
    ## TODO refactor base.mako to inherit from another, higher level
    ## template with just the assets to avoid this css magic /hrybacki
    <style>
          .footer, .copyright, .osf-nav-wrapper  {
            display: none;
          }
    </style>

    <form class="form col-md-4 col-md-offset-4"
            id="twoFactorSignInForm"
            class="form"
            % if next_url:
                action="/login/two-factor/?next=${next_url}"
            % else:
                action="/login/two-factor/"
            % endif
            method="POST"
            name="signin"
        >
        <div class="panel panel-primary">
            <div class="panel-heading">Two Factor Code</div>
                <div class="panel-body">
                    <input type="text" class="form-control" name="twoFactorCode" placeholder="Enter two factor code" />
                    <button type="submit" class="btn btn-success pull-right m-t-md">Verify</button>
                </div>
        </div>
        <hr class="m-t-lg m-b-sm"/>
        <h6 class="text-center text-muted text-300"><a href="${ web_url_for('auth_login') }">Back to OSF</a></h6>
    </form>

</%def>

<%def name="javascript_bottom()">
    <script src=${"/static/public/js/twofactor-page.js" | webpack_asset}></script>
</%def>