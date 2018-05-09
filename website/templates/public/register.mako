<%inherit file="base.mako"/>

<%def name="title()">Sign Up</%def>

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

    %if campaign == "osf-registries":
        <div class="text-center m-t-lg">
            <h3>OSF Registries</h3><hr>
            <p>Please login to the Open Science Framework or create a free account to continue.</p>
        </div>
    %endif

    %if campaign == "osf-preprints":
        <div class="text-center m-t-lg">
            <h3>OSF Preprints</h3><hr>
            <p>Please login to the Open Science Framework or create a free account to contribute to OSF Preprints.</p>
        </div>
    %endif

    %for provider in preprint_campaigns.keys():
        %if campaign == provider:
            <div class="text-center m-t-lg">
                <h3>${preprint_campaigns[provider]['name'] | n}</h3><hr>
            </div>
        %endif
    %endfor

    <div class="row m-t-xl">
    %if campaign != "institution" or not enable_institutions:
        <div id="signUpScope" class="col-sm-10 col-sm-offset-1 col-md-9 col-md-offset-2 col-lg-8 signup-form p-b-md m-b-m bg-color-light">
            <form data-bind="submit: submit" class="form-horizontal">

                %if campaign == "prereg":
                     <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/registries/osf-prereg-black.png" style="width: 200px; margin-top: 15px" /></td>
                            <td><h3>Create a free OSF account</h3></td>
                        </tr>
                    </table>
                %elif campaign == "osf-registries":
                     <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/registries/osf-registries-black.png" style="width: 200px; margin-top: 15px" /></td>
                            <td><h3>Create a free OSF account</h3></td>
                        </tr>
                    </table>
                %elif campaign == "osf-registered-reports":
                     <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/registries/osf-registries-black.png" style="width: 200px; margin-top: 15px" /></td>
                            <td><h3>Create a free OSF account</h3></td>
                        </tr>
                    </table>
                %elif campaign == "osf-preprints":
                     <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                        <tr>
                            <td><img src="/static/img/preprint_providers/osf-preprints-login.png" style="width: 200px; margin-top: 15px" /></td>
                            <td><h3>Create a free OSF account</h3></td>
                        </tr>
                    </table>
                %elif campaign not in preprint_campaigns.keys():
                    <h3 class="m-b-lg"> Create a free account </h3>
                %else:
                    %for provider in preprint_campaigns.keys():
                        %if campaign == provider:
                            <table style="border-collapse: separate; border-spacing: 30px 0; margin-top: 20px;  margin-bottom: 10px;">
                                <tr>
                                    <td><img src="${preprint_campaigns[provider]['logo_path']}" style="width: 100px; height: 100px" /></td>
                                    <td><h3>Create a free OSF account to contribute to ${preprint_campaigns[provider]['name'] | n}</h3></td>
                                </tr>
                            </table>
                        %endif
                    %endfor
                %endif

                <div class="form-group" data-bind=" css: { 'has-error': fullName() && !fullName.isValid(), 'has-success': fullName() && fullName.isValid() }">
                    <label for="inputName" class="col-sm-4 control-label">Full Name</label>
                    <div class="col-sm-8">
                        ## Maxlength for full names must be 186 - quickfile titles use fullname + 's Quick Files
                        <input autofocus type="text" class="form-control" id="inputName" placeholder="Name" data-bind="value: fullName, disable: submitted(), event: { blur: trim.bind($data, fullName) }" maxlength="186">
                        <p class="help-block" data-bind="validationMessage: fullName" style="display: none;"></p>
                    </div>
                </div>
                <div class="form-group" data-bind="css: { 'has-error': email1() && !email1.isValid(), 'has-success': email1() && email1.isValid() }" >
                    <label for="inputEmail" class="col-sm-4 control-label">Email</label>
                    <div class="col-sm-8">
                        <input type="text" class="form-control" id="inputEmail" placeholder="Email" data-bind="value: email1, disable: submitted(), event: { blur: trim.bind($data, email1) }" maxlength="255">
                        <p class="help-block" data-bind="validationMessage: email1" style="display: none;"></p>
                    </div>
                </div>
                <div class="form-group" data-bind="css: { 'has-error': email2() && !email2.isValid(), 'has-success': email2() && email2.isValid() }">
                    <label for="inputEmail2" class="col-sm-4 control-label">Confirm Email</label>
                    <div class="col-sm-8">
                        <input type="text" class="form-control" id="inputEmail2" placeholder="Re-enter email" data-bind=" value: email2, disable: submitted(), event: { blur: trim.bind($data, email2) }" maxlength="255">
                        <p class="help-block" data-bind="validationMessage: email2" style="display: none;"></p>
                    </div>
                </div>
                <div class="form-group" data-bind="css: { 'has-error': password() && !password.isValid(), 'has-success': password() && password.isValid() }">
                    <label for="inputPassword3" class="col-sm-4 control-label">Password</label>
                    <div class="col-sm-8">
                        <input type="password" class="form-control" id="inputPassword3" placeholder="Password" data-bind="textInput: typedPassword, value: password, disable: submitted(), event: { blur: trim.bind($data, password) }" maxlength="256">
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
        <script src="https://recaptcha.net/recaptcha/api.js" async defer></script>
    %endif
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>
