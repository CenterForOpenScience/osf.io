<%inherit file="base.mako"/>

<%def name="title()">Home</%def>

<%def name="content()">
    <div class="row hpContainerOne">
        <div class="col-sm-8 col-md-7">
            <p class="hpHeadOne">Project management with collaborators,<br> project sharing with the public</p>
            <br>
            <p class="hpSubHeadOne">The Open Science Framework (OSF) supports the entire research lifecycle: planning, execution, reporting, archiving, and discovery.</p>
        </div>
        <div id="signUpScope" class="col-sm-4 col-md-offset-1 img-rounded hpSignUp">
            <form data-bind="submit: submit, css: {hideValidation: !showValidation()}">
                <div class="form-group" data-bind="css: {'has-error': fullName() && !fullName.isValid()}">
                    <label class="placeholder-replace" style="display:none">Full Name</label>
                    <input class="form-control" placeholder="Full Name" data-bind="
                        value: fullName,
                        valueUpdate: 'input',
                        disable: submitted(),
                        event: {
                            focus: hideValidation,
                            blur: trim.bind($data, fullName)
                        }"/>
                </div>
                <div class="form-group" data-bind="css: {'has-error': email1() && !email1.isValid()}">
                    <label class="placeholder-replace" style="display:none">Contact Email</label>
                    <input class="form-control" placeholder="Contact Email" data-bind="
                        value: email1,
                        valueUpdate: 'input',
                        disable: submitted(),
                        event: {
                            focus: hideValidation,
                            blur: trim.bind($data, email1)
                        }"/>
                </div>
                <div class="form-group" data-bind="css: {'has-error': email2() && !email2.isValid()}">
                    <label class="placeholder-replace" style="display:none">Confirm Email</label>
                    <input class="form-control" placeholder="Confirm Email" data-bind="
                        value: email2,
                        valueUpdate: 'input',
                        disable: submitted(),
                        event: {
                            focus: hideValidation,
                            blur: trim.bind($data, email2)
                        }"/>
                </div>
                <div class="form-group" data-bind="css: {'has-error': password() && !password.isValid()}">
                    <label class="placeholder-replace" style="display:none">Password</label>
                    <input type="password" class="form-control" placeholder="Password" data-bind="
                        value: password,
                        valueUpdate: 'input',
                        disable: submitted(),
                        event: {
                            focus: hideValidation
                            blur: trim.bind($data, password)
                        }"/>
                </div>
                <!-- Flashed Messages -->
                <div class="help-block">
                    <p data-bind="html: flashMessage, attr.class: flashMessageClass"></p>
                </div>
                <div class="text-right">
                    <button type="submit" class="btn btn-danger" data-bind="visible: !submitted()">Sign up</button>
                </div>
            </form>
        </div><!-- end #signUpScope -->
    </div>
    <div class="row text-center hpHeader">
        <div class="col-md-12">
            <p class="hpHeadTwo">What can the OSF do for you?</p>
            <p class="hpSubHeadOne">Provide features to increase the efficiency and effectiveness of your research</p>
        </div>
    </div>
    <div class="row text-center">
        <div class="col-sm-4 hpFeature">
            <img id="connect" src="/static/img/outlet.gif">
            <div class="hpSubHeadTwo">CONNECTIONS</div>
            <p>with the services you already use</p>
            <div class="hpFeatureInfo">Link services to simplify transitions and facilitate interactions; e.g., connect OSF to your Dropbox, GitHub, and Amazon S3 repositories and all four work together!</div>
        </div>
        <div class="col-sm-4 hpFeature">
            <img id="archive" src="/static/img/filedrawer.gif"><br>
            <div class="hpSubHeadTwo">ARCHIVING</div>
            <p>and managing collaborations</p>
            <div class="hpFeatureInfo">Spend more time doing your research and less time keeping track of it. No more lost data from crashed drives, disappearing collaborators, or failing memories.</div>
        </div>
        <div class="col-sm-4 hpFeature">
            <img id="integrate" src="/static/img/padlock.gif">
            <div class="hpSubHeadTwo">CONTROL</div>
            <p>over private and public workflows</p>
            <div class="hpFeatureInfo">Work privately among collaborators and, when you wish, make some or all of your research materials public for others to use and cite.</div>
        </div>
    </div>
    <div class="row text-center hpHeader">
        <div class="col-md-12">
            <p class="hpHeadTwo">Free and easy to use</p>
            <p class="hpSubHeadOne">Follow these simple steps to get started. We'll be <a class="hpLink" href="mailto:contact@osf.io">here to help</a> the whole way.</p>
        </div>
    </div>
    <div class="row text-center">
        <div class="col-md-12">
            <p class="hpSubHeadThree hpSteps"><a class="hpLink" href="/account/">Sign up.</a></p>
            <p class="hpSubHeadThree hpSteps"><a class="hpLink" href="/getting-started/">Learn how to build a project.</a></p>
            <p class="hpSubHeadThree hpSteps"><a class="hpLink" href="/explore/activity/">Get inspired.</a></p>
        </div>
    </div>
    <div class="row text-center">
        <div class="col-md-12">
            <p class="hpStepsText">Want more than an answer to a quick question? Feel free to <a class="hpLink" href="mailto:contact@osf.io">email us</a> to schedule a help session or tutorial for you and your collaborators.<br>OSF is maintained by the non-profit <a class="hpLink" href="http://centerforopenscience.org/">Center for Open Science</a>.</p>
        </div>
    </div>
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src=${"/static/public/js/home-page.js" | webpack_asset}></script>
</%def>
