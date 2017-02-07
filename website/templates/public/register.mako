<%inherit file="base.mako"/>

<%def name="title()">Sign In</%def>

<%def name="content()">

    %if campaign == "prereg":
        <div class="text-center m-t-lg">
            <h3>Preregistration Challenge</h3><hr>
            <p>Please login to the Open Science Framework or create a free account to continue.</p>
        </div>
    %endif

    %if campaign == "erpc":
        <div class="text-center m-t-lg">
            <h3>Election Research Preacceptance Competition</h3><hr>
            <p>Please login to the Open Science Framework or create a free account to continue.</p>
        </div>
    %endif

    %if campaign == "osf-preprints":
        <div class="text-center m-t-lg">
            <h3>OSF Preprints</h3><hr>
            <p>Please login to the Open Science Framework or create a free account to contribute to OSF Preprints.</p>
        </div>
    %endif

    %if campaign == "socarxiv-preprints":
        <div class="text-center m-t-lg">
            <h3>SocArXiv Preprints</h3><hr>
        </div>
    %endif

    %if campaign == "engrxiv-preprints":
        <div class="text-center m-t-lg">
            <h3>engrXiv Preprints</h3><hr>
        </div>
    %endif

    %if campaign == "psyarxiv-preprints":
        <div class="text-center m-t-lg">
            <h3>PsyArXiv Preprints</h3><hr>
        </div>
    %endif

    <div class="row m-t-xl">
    %if campaign != "institution" or not enable_institutions:
        <div id="signUpScope" class="col-sm-10 col-sm-offset-1 col-md-9 col-md-offset-2 col-lg-8 signup-form p-b-md m-b-m bg-color-light">
            <form data-bind="submit: submit" class="form-horizontal">

                %if campaign == "osf-preprints":
                     <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/preprint_providers/osf-preprints-login.png" style="width: 200px; margin-top: 15px" /></td>
                            <td><h3>Create a free OSF account</h3></td>
                        </tr>
                    </table>
                %elif campaign == "socarxiv-preprints":
                    <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/preprint_providers/socarxiv-login.png" style="width: 150px; background: #e14b5a;" /></td>
                            <td><h3>Create a free OSF account to contribute to SocArXiv</h3></td>
                        </tr>
                    </table>
                %elif campaign == "engrxiv-preprints":
                    <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/preprint_providers/engrxiv-login.png" style="width: 150px; background: #222F38;" /></td>
                            <td><h3>Create a free OSF account to contribute to engrXiv</h3></td>
                        </tr>
                    </table>
                %elif campaign == "psyarxiv-preprints":
                    <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/preprint_providers/psyarxiv-login.png" style="width: 150px; background: #a9a9a9; padding: 0 10px 0 10px;" /></td>
                            <td><h3>Create a free OSF account to contribute to PsyArXiv</h3></td>
                        </tr>
                    </table>
                %elif campaign == "scielo-preprints":
                    <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/preprint_providers/scielo-login.png" style="width: 150px; padding: 0 10px 0 10px;" /></td>
                            <td><h3>Create a free OSF account to contribute to SciELO</h3></td>
                        </tr>
                    </table>
                %elif campaign == "agrixiv-preprints":
                    <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/preprint_providers/agrixiv-login.svg" style="width: 150px; padding: 0 10px 0 10px;" /></td>
                            <td><h3>Create a free OSF account to contribute to AgriXiv</h3></td>
                        </tr>
                    </table>
                %else:
                    <h3 class="m-b-lg"> Create a free account </h3>
                %endif

                <div class="form-group" data-bind=" css: { 'has-error': fullName() && !fullName.isValid(), 'has-success': fullName() && fullName.isValid() }">
                    <label for="inputName" class="col-sm-4 control-label">Full Name</label>
                    <div class="col-sm-8">
                        <input autofocus type="text" class="form-control" id="inputName" placeholder="Name" data-bind="value: fullName, disable: submitted(), event: { blur: trim.bind($data, fullName) }">
                        <p class="help-block" data-bind="validationMessage: fullName" style="display: none;"></p>
                    </div>
                </div>
                <div class="form-group" data-bind="css: { 'has-error': email1() && !email1.isValid(), 'has-success': email1() && email1.isValid() }" >
                    <label for="inputEmail" class="col-sm-4 control-label">Email</label>
                    <div class="col-sm-8">
                        <input type="text" class="form-control" id="inputEmail" placeholder="Email" data-bind="value: email1, disable: submitted(), event: { blur: trim.bind($data, email1) }">
                        <p class="help-block" data-bind="validationMessage: email1" style="display: none;"></p>
                    </div>
                </div>
                <div class="form-group" data-bind="css: { 'has-error': email2() && !email2.isValid(), 'has-success': email2() && email2.isValid() }">
                    <label for="inputEmail2" class="col-sm-4 control-label">Confirm Email</label>
                    <div class="col-sm-8">
                        <input type="text" class="form-control" id="inputEmail2" placeholder="Re-enter email" data-bind=" value: email2, disable: submitted(), event: { blur: trim.bind($data, email2) }">
                        <p class="help-block" data-bind="validationMessage: email2" style="display: none;"></p>
                    </div>
                </div>
                <div class="form-group" data-bind="css: { 'has-error': password() && !password.isValid(), 'has-success': password() && password.isValid() }">
                    <label for="inputPassword3" class="col-sm-4 control-label">Password</label>
                    <div class="col-sm-8">
                        <input type="password" class="form-control" id="inputPassword3" placeholder="Password" data-bind="textInput: typedPassword, value: password, disable: submitted(), event: { blur: trim.bind($data, password) }">
                        <div class="row" data-bind="visible: typedPassword().length > 0">
                            <div class="col-xs-8">
                                <div class="progress create-password">
                                    <div class="progress-bar progress-bar-sm" role="progressbar" data-bind="attr: passwordComplexityInfo().attr"></div>
                                </div>
                            </div>
                            <div class="col-xs-4 f-w-xl">
                                <!-- ko if: passwordFeedback() -->
                                <p id="front-password-info" data-bind="text: passwordComplexityInfo().text, attr: passwordComplexityInfo().text_attr"></p>
                                <!-- /ko -->
                            </div>
                        </div>

                        <div>
                            <!-- ko if: passwordFeedback() -->
                                <p class="help-block osf-box-lt p-xs" data-bind="validationMessage: password" style="display: none;"></p>
                                <p class="help-block osf-box-lt " data-bind="css : { 'p-xs': passwordFeedback().warning }, visible: typedPassword().length > 0, text: passwordFeedback().warning"></p>
                            <!-- /ko -->
                        </div>
                    </div>
                    <!-- Flashed Messages -->
                    <div class="col-sm-12">
                        <div class="help-block osf-box-lt">
                            <p data-bind="html: message, attr: {class: messageClass}"></p>
                        </div>
                    </div>
                </div>
                </br>
                <div class="form-group m-t-md">
                    <div class="col-md-5 col-sm-12" style="padding-left: 25px">
                        <a href="${non_institution_login_url}" >Already have an account?</a>
                        <br>
                        <a href="${institution_login_url}">Login through your institution  <i class="fa fa-arrow-right"></i></a>
                    </div>
                    <div class="col-md-7 col-sm-12">
                        %if recaptcha_site_key:
                            <div class="col-xs-12">
                                <div class="pull-right g-recaptcha" data-sitekey="${recaptcha_site_key}"></div>
                            </div>
                        %endif
                            <div class="col-xs-12">
                                <span class="pull-right p-t-sm"><button type="submit" class="btn btn-success" data-bind="disable: submitted()">Create account</button></span>
                            </div>
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
        });
    </script>
    <script src=${"/static/public/js/login-page.js" | webpack_asset}></script>
    %if recaptcha_site_key:
        <script src="https://www.google.com/recaptcha/api.js" async defer></script>
    %endif
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>
