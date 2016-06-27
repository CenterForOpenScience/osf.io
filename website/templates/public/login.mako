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
    <div class="row m-t-xl">
    %if campaign == "institution" and enable_institutions:
        <div class="col-sm-6 col-sm-offset-3">
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
                            <p>For non-institutional login, click <a href="${login_url}">here</a>.</p>
                    </div>
                </div>
            </div>
        </div>
    %endif
    %if campaign != "institution" or not enable_institutions:
        <div id="signUpScope" class="col-sm-6 col-sm-offset-3 signup-form p-b-md m-b-m bg-color-light">
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
                                autofocus
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
                            textInput: typedPassword,
                            value: password,
                            disable: submitted(),
                            event: {
                                blur: trim.bind($data, password)
                            }"
                        >
                          <div class="progress create-password">
                              <div class="progress-bar progress-bar-sm" role="progressbar" data-bind="attr: passwordComplexityInfo().attr"></div>
                          </div>
                        <!-- ko if: passwordFeedback() -->
                        <p class="text-right" data-bind="text: passwordComplexityInfo().text, attr: passwordComplexityInfo().text_attr"></p>
                        <p class="help-block osf-box-lt" data-bind="validationMessage: password" style="display: none;"></p>
                        <p class="help-block osf-box-lt" data-bind="text: passwordFeedback().warning"></p>
                        <!-- /ko -->
                    </div>
                </div>
                <!-- Flashed Messages -->
                <div class="help-block" >
                    <p class="m-l-md" data-bind="html: flashMessage, attr: {class: flashMessageClass}"></p>
                </div>
                </br>
                <div class="form-group">
                    <div class="col-md-8 col-sm-12" style="padding-left: 25px">
                        <a href="${login_url}" >Already have an account?</a>
                    </div>
                    %if redirect_url:
                        <div class="col-md-8 col-sm-12" style="padding-left: 25px">
                            <a href="${domain}login/?campaign=institution&redirect_url=${redirect_url}">Login through your institution  <i class="fa fa-arrow-right"></i></a>
                        </div>
                    %else:
                        <div class="col-md-8 col-sm-12" style="padding-left: 25px">
                            <a href="${domain}login/?campaign=institution">Login through your institution  <i class="fa fa-arrow-right"></i></a>
                        </div>
                    %endif
                    <div class="col-md-4 col-sm-12">
                        <button type="submit" class="btn pull-right btn-success" data-bind="css: {disabled: !password.isValid()}">Create account</button>
                    </div>
                </div>
            </form>
        </div>
        <div class="row">
            <div id="termsAndConditions" class="m-t-md col-sm-6 col-sm-offset-3">
                <p> By clicking "Create account", you agree to our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/TERMS_OF_USE.md">Terms</a> and that you have read our <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md">Privacy Policy</a>, including our information on <a href="https://github.com/CenterForOpenScience/centerforopenscience.org/blob/master/PRIVACY_POLICY.md#f-cookies">Cookie Use</a>.</p>
            </div>
        </div>
    </div>
    %endif
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            'campaign': ${ campaign or '' | sjson, n },
            'institution_redirect': ${ institution_redirect or '' | sjson, n }
        });
    </script>
    <script src=${"/static/public/js/login-page.js" | webpack_asset}></script>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>
