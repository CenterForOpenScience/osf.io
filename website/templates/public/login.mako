<%inherit file="base.mako"/>

<%def name="title()">Sign In</%def>

<%def name="content()">

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
    <h3>OSF for Institutions </h3>
    <hr>
    <p>
      If your institution has partnered with the Open Science Framework, please
        select its name below and sign in with your institutional credentials.
    </p>
    <p> If you do not currently have an OSF account, this will create one. By creating an account you agree to our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/TERMS_OF_USE.md">Terms</a> and that you have read our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>, including our information on <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md#f-cookies">Cookie Use</a>.</p>
</div>
%endif
%if existing_user:
    <div class="row m-t-xl existing-user-container">
%else:
    <div class="row m-t-xl">
%endif
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
                    <button data-bind="click: instLogin, css: {disabled: loading}" class="btn btn-success pull-right">Sign in</button>
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
%if campaign != "institution" or not enable_institutions:
    %if existing_user:
        <div class="col-sm-6 col-sm-offset-3">
            <div class="text-center">
                <h1 class="login-title">Open Science Framework</h1>
                <div class="login-logo"></div>
            </div>
            <h3 class="existing-user-instructions">Please sign in as <b>${existing_user}</b> to continue.</h3>
        </div>
        <div class="col-sm-6 col-sm-offset-3 existing-user-signin p-b-md m-b-m">
    %elif sign_up:
        <div class="col-sm-5 col-sm-offset-1 toggle-box toggle-box-left toggle-box-muted p-h-lg">
    %else:
        <div class="col-sm-5 col-sm-offset-1 toggle-box toggle-box-left toggle-box-active p-h-lg">
    %endif
        <form
            id="logInForm"
            class="form-horizontal"
            action="${login_url}"
            method="POST"
            data-bind="submit: submit"
        >
        <h3 class=${'m-b-lg' if not existing_user else 'm-b-lg m-l-md'}> Login </h3>
        <div class="form-group">
            <label for="inputEmail3" class="col-sm-2 control-label">Email</label>
            <div class="col-sm-10">
                <input
                    ${'autofocus' if not sign_up else ''}
                    type="email"
                    class="form-control"
                    data-bind="value: username"
                    name="username"
                    id="inputEmail3"
                    placeholder="Email"
                >
            </div>
        </div>
            <div class="form-group">
                <label for="inputPassword3" class="col-sm-2 control-label">Password</label>
                    <div class="col-sm-10">
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
            %if existing_user:
            <div class="col-sm-12 m-t-sm">
            <div class="form-group col-sm-7 remember-me-checkbox">
                    <div class="checkbox">
                    <label><input type="checkbox"> Remember me</label>
                </div>
            </div>
                 <div class="form-group pull-right">
                    <button type="submit" class="btn btn-success">Sign in</button>
                </div>
            </div>
            <div class="col-sm-8 login-forgot-password">
                <a href="/forgotpassword/">Forgot password?</a>
            </div>
            %else:
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
            %endif
        </form>
    </div>
    %if not existing_user:
        %if sign_up:
            <div id="signUpScope" class="col-sm-5 toggle-box toggle-box-right toggle-box-active p-h-lg" style="height: auto;">
        %else:
            <div id="signUpScope" class="col-sm-5 toggle-box toggle-box-right toggle-box-muted p-h-lg" style="height: auto;">
        %endif
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
                            ${'autofocus' if sign_up else ''}
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
            <div>
                <p> By clicking "Create account", you agree to our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/TERMS_OF_USE.md">Terms</a> and that you have read our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>, including our information on <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md#f-cookies">Cookie Use</a>.</p>
            </div>
            <div class="form-group">
                <div class="col-sm-offset-4 col-sm-8">
                    <button type="submit" class="btn pull-right btn-success ">Create account</button>
                </div>
            </div>
        </form>
    </div>

</div>

        </div>
    </div>
    %else:
        <div id="signUpScope"></div>
    %endif
%endif
            %if redirect_url:
            <div class="text-center m-b-sm col-sm-12" style="padding-top: 15px"> <a href="${domain}login/?campaign=institution&redirect_url=${redirect_url}">Login through your institution  <i class="fa fa-arrow-right"></i></a></div>
        %else:
            <div class="text-center m-b-sm col-sm-12" style="padding-top: 15px"> <a href="${domain}login/?campaign=institution">Login through your institution  <i class="fa fa-arrow-right"></i></a></div>
        %endif
    %endif
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            'campaign': ${campaign or '' | sjson, n},
            'institution_redirect': ${institution_redirect or '' | sjson, n},
            'existing_user': ${existing_user or '' | sjson, n}
        });
    </script>
    <script src=${"/static/public/js/login-page.js" | webpack_asset}></script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}

    <link rel="stylesheet" href="/static/css/pages/login-page.css">
</%def>
