<%inherit file="base.mako"/>

<%def name="title()">Sign In</%def>

<%def name="content_wrap()">
    <div class="watermarked">
            % if status:
                <%include file="alert.mako" args="extra_css='alert-front text-center'"/>
            % endif
            ${self.content()}
    </div><!-- end watermarked -->
</%def>

<%def name="content()">

        <div id="login-hero">
        <div class="container text-center">
            <div class="visible-xs-block visible-sm-block visible-md-block network-bg"></div>
            %if campaign == "institution" and enable_institutions:

            <h1 class="hero-brand">OSF For Institutions</h1>
            %else:
            <h1 class="hero-brand">Open Science Framework</h1>
            %endif

            <h3 class="login-tagline">A scholarly commons to connect the entire research cycle</h3>
        </div>
%if campaign == "prereg":
<div class="text-center m-t-lg">
    <h3>Preregistration Challenge </h3>
    <hr>
    <p>
      Please login to the Open Science Framework or create a free account to continue.
    </p>
</div>
%endif

%if campaign == "institution" and enable_institutions:
<div class="text-center m-t-lg">
    <h4>
      If your institution has partnered with the Open Science Framework, please
        select its name below and sign in with your institutional credentials.
    </h4>
</div>
%endif
<div class="row m-t-xl">

    %if campaign == "institution" and enable_institutions:
    <div class="col-sm-6 col-sm-offset-3 toggle-box toggle-box-active">
        <h3 class="m-b-lg"> Login through institution</h3>
        <div id="inst">
            <div class="form-group">
                <label for="selectedInst" class="control-label">Select Institution</label>
                <select id="selectedInst" class="form-control" data-bind="value: selectedInst, options: instNames"></select>
            </div>
            <div class="form-group">
                <div class="col-sm-offset-3 col-sm-9">
                    <button data-bind="click: instLogin" class="btn btn-success pull-right">Sign in</button>
                </div>
            </div>
            <div class="form-group" style="padding-top: 15px">
                <div class="text-center m-t-lg">
                    <p>For non-institutional login, click <a href="/login/">here</a>.</p>
                </div>
            </div>
        </div>
    </div>
    %endif
      %if campaign == "merge_user":
    <div class="col-sm-6 col-sm-offset-4 p-h-lg">
      <h4>Please log in to continue</h4>
        <form
            id="logInForm"
            class="form-horizontal"
            action="${login_url}"
            method="POST"
            data-bind="submit: submit"
        >
            <div class="form-group">
                <div class="col-sm-8">
                    <input
                        type="email"
                        class="form-control"
                        data-bind="value: username"
                        name="username"
                        id="inputEmail3"
                        placeholder="Email"
                        autofocus
                    >
                </div>
            </div>
            <div class="form-group">
                    <div class="col-sm-8">
                    <input
                        type="password"
                        class="form-control"
                        id="inputPassword3"
                        placeholder="Password"
                        data-bind="value: password"
                        name="password"
                    >
                </div>
            </div>
                <div class="col-sm-8">
            <div class="form-group col-sm-4">
                    <div class="checkbox">
                    <label><input type="checkbox"> Remember me</label>
                    </div>
            </div>
            <div class="form-group col-sm-9">
                    <button type="submit" class="btn btn-success pull-right">Sign in</button>
                </div>
        </form>
    </div>

    %endif

    %if (campaign != "institution" or not enable_institutions) and campaign != "merge_user":

      <div class="text-center m-t-lg">
          <h3>Add an email to your account </h3>
          <hr>
          <p>
              Please login to the Open Science Framework or create a free account to continue.
          </p>
      </div>

      <div class="col-sm-5 col-sm-offset-1 toggle-box toggle-box-left toggle-box-active p-h-lg">
          <form
            id="logInForm"
            class="form-horizontal"
            action="${login_url}"
            method="POST"
            data-bind="submit: submit"
        >
            <h3 class="m-b-lg"> Login </h3>
            <div class="form-group">
                <label for="inputEmail3" class="col-sm-3 control-label">Email</label>
                <div class="col-sm-9">
                    <input
                        type="email"
                        class="form-control"
                        data-bind="value: username"
                        name="username"
                        id="inputEmail3"
                        placeholder="Email"
                        autofocus
                    >
                </div>
            </div>
            <div class="form-group">
                <label for="inputPassword3" class="col-sm-3 control-label">Password</label>
                    <div class="col-sm-9">
                    <input
                        type="password"
                        class="form-control"
                        id="inputPassword3"
                        placeholder="Password"
                        data-bind="value: password"
                        name="password"
                    >
                </div>
            </div>
            <div class="form-group">
                <div class="col-sm-offset-3 col-sm-9">
                    <div class="checkbox">
                    <label><input type="checkbox"> Remember me</label>
                    </div>
                </div>
            </div>
            <div class="form-group">
                <div class="col-sm-offset-3 col-sm-9">
                    <button type="submit" class="btn btn-success pull-right">Sign in</button>
                </div>
            </div>
        </form>
    </div>
    <div id="signUpScope" class="col-sm-5 toggle-box toggle-box-right toggle-box-muted p-h-lg" style="height: auto;">
        <form data-bind="submit: submit" class="form-horizontal">
            <h3 class="m-b-lg"> Create a free account </h3>
                <div
                    class="form-group"
                    data-bind="
                        css: {
                            'has-error': fullName() && !fullName.isValid(),
                            'has-success': fullName() && fullName.isValid()
                        }"
                >
                    <label for="inputName" class="col-sm-4 control-label">Full Name</label>
                    <div class="col-sm-8">
                        <input
                            type="text"
                            class="form-control"
                            id="inputName"
                            placeholder="Name"
                            data-bind="
                                value: fullName, disable: submitted(),
                                event: {
                                    blur: trim.bind($data, fullName)
                                }"
                        >
                        <p class="help-block" data-bind="validationMessage: fullName" style="display: none;"></p>
                    </div>
                </div>
            <div
                class="form-group"
                data-bind="
                    css: {
                        'has-error': email1() && !email1.isValid(),
                        'has-success': email1() && email1.isValid()
                    }"
            >
                <label for="inputEmail" class="col-sm-4 control-label">Email</label>
                <div class="col-sm-8">
                    <input
                        type="text"
                        class="form-control"
                        id="inputEmail"
                        placeholder="Email"
                        data-bind="
                            value: email1,
                            disable: submitted(),
                            event: {
                                blur: trim.bind($data, email1)
                            }"
                    >
                    <p class="help-block" data-bind="validationMessage: email1" style="display: none;"></p>
                </div>
            </div>
            <div
                class="form-group"
                data-bind="
                    css: {
                        'has-error': email2() && !email2.isValid(),
                        'has-success': email2() && email2.isValid()
                    }"
            >
                <label for="inputEmail2" class="col-sm-4 control-label">Confirm Email</label>
                <div class="col-sm-8">
                    <input
                        type="text"
                        class="form-control"
                        id="inputEmail2"
                        placeholder="Re-enter email"
                        data-bind="
                            value: email2,
                            disable: submitted(),
                            event: {
                                blur: trim.bind($data, email2)
                            }"
                    >
                    <p class="help-block" data-bind="validationMessage: email2" style="display: none;"></p>
                </div>
            </div>
            <div
                class="form-group"
                data-bind="
                    css: {
                        'has-error': password() && !password.isValid(),
                        'has-success': password() && password.isValid()
                    }"
            >
                <label for="inputPassword3" class="col-sm-4 control-label">Password</label>
                <div class="col-sm-8">
                    <input
                        type="password"
                        class="form-control"
                        id="inputPassword3"
                        placeholder="Password"
                        data-bind="
                            value: password,
                            disable: submitted(),
                            event: {
                                blur: trim.bind($data, password)
                            }"
                    >
                    <p class="help-block" data-bind="validationMessage: password" style="display: none;"></p>
                </div>
            </div>
            <!-- Flashed Messages -->
            <div class="help-block" >
                <p data-bind="html: flashMessage, attr.class: flashMessageClass"></p>
            </div>
            <div class="form-group">
                <div class="col-sm-offset-4 col-sm-8">
                    <button type="submit" class="btn pull-right btn-success ">Create account</button>
                </div>
            </div>
        </form>
    </div>

    %endif
                        </div>

</div>

</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            'campaign': ${campaign or '' | sjson, n}
        });
    </script>
    <script src=${"/static/public/js/login-page.js" | webpack_asset}></script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/home-page.css">
    <link rel="stylesheet" href="/static/css/front-page.css">
    <link rel="stylesheet" href="/static/css/pages/login-page.css">
</%def>
