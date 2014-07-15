<%inherit file="base.mako"/>
<%def name="title()">Home</%def>
<%def name="content()">
    <div id="hpContainerOne">
        <div id="containerOneHeader" class="col-md-6">
            <p class="headOne">Project management with collaborators,<br> project sharing with the public</p>
            <br>
            <p class="subHeadOne">The Open Science Framework (OSF) supports the entire research lifecycle: planning, execution, reporting, archiving, and discovery. </p>
        </div>
        <div id="signUpScope" class="sign-up img-rounded col-md-4">

            <form data-bind="submit: submit, css: {hideValidation: !showValidation()}">

                <div
                        class="form-group"
                        data-bind="css: {'has-error': fullName() && !fullName.isValid()}">
                    <input
                            class="form-control"
                            placeholder="Full Name"
                            data-bind="value: fullName,
                                       valueUpdate: 'input',
                                       disable: submitted(),
                                       event: {
                                           focus: hideValidation,
                                           blur: trim.bind($data, fullName)
                                       }"
                        />
                </div>

                <div
                        class="form-group"
                        data-bind="css: {'has-error': email1() && !email1.isValid()}">
                    <input
                            class="form-control"
                            placeholder="Contact Email"
                            data-bind="value: email1,
                                       valueUpdate: 'input',
                                       disable: submitted(),
                                       event: {
                                           focus: hideValidation,
                                           blur: trim.bind($data, email1)
                                       }"
                        />
                </div>

                <div
                        class="form-group"
                        data-bind="css: {'has-error': email2() && !email2.isValid()}">
                    <input
                            class="form-control"
                            placeholder="Confirm Email"
                            data-bind="value: email2,
                                       valueUpdate: 'input',
                                       disable: submitted(),
                                       event: {
                                           focus: hideValidation,
                                           blur: trim.bind($data, email2)
                                       }"
                        />
                </div>

                <div
                        class="form-group"
                        data-bind="css: {'has-error': password() && !password.isValid()}">
                    <input
                            type="password"
                            class="form-control"
                            placeholder="Password"
                            data-bind="value: password,
                                       valueUpdate: 'input',
                                       disable: submitted(),
                                       event: {
                                           focus: hideValidation
                                           blur: trim.bind($data, password)
                                       }"
                        />
                </div>

                <!-- Flashed Messages -->
                <div class="help-block">
                    <p data-bind="html: flashMessage, attr.class: flashMessageClass"></p>
                </div>

                <div>
                    <button
                            type="submit"
                            class="btn btn-danger"
                            data-bind="visible: !submitted()"
                        >Sign up</button>
                </div>

            </form>

        </div><!-- end #signUpScope -->
    </div>
    <div id="hpContainerTwo" class="row">
        <div class="header text-center col-md-12">
            <p class="headTwo">What can the OSF do for you?</p>
            <p class="subHeadOne">Provide features to increase the efficiency and effectiveness of your research</p>
        </div>
        <div class="col-md-12 featureDescriptions">
            <div class="col-md-4 text-center connect">
                <img id="connect" src="/static/img/outlet.gif">
                <div class="subHeadTwo text-center">CONNECTIONS</div>
                <p>with the services you already use</p>
                <div class="featureInfo">Link services to simplify transitions and facilitate interactions; e.g., connect OSF to your Dropbox, GitHub, and Amazon S3 repositories and all four work together!</div>
            </div>
            <div class="col-md-4 text-center archive">
                <img id="archive" src="/static/img/filedrawer.gif"><br>
                <div class="subHeadTwo text-center">ARCHIVING</div>
                <p>and management of research and collaborations</p>
                <div class="featureInfo">Spend more time doing your research and less time keeping track of it. No more lost data from crashed drives, disappearing collaborators, or failing memories.</div>
            </div>

            <div class="col-md-4 text-center integrate">
                <img id="integrate" src="/static/img/padlock.gif">
                <div class="subHeadTwo">CONTROL</div>
                <p>over private and public workflows</p>
                <div class="featureInfo">Work privately among collaborators and, when you wish, make some or all of your research materials public for others to use and cite.</div>
            </div>
        </div>
    </div>
    <div id="hpContainerThree" class="row">
        <div class="header text-center col-md-12">
            <p class="headTwo">Free and easy to use</p>
            <p class="subHeadOne">Follow these simple steps to get started. We'll be <a class="hpLink" href="mailto:contact@osf.io">here to help</a> the whole way.</p>
            <div class="col-md-12 padded">
                <p class="subHeadThree steps"><a class="hpLink" href="https://osf.io/account/">Sign up.</a></p>
                <p class="subHeadThree steps"><a class="hpLink" href="https://osf.io/getting-started/">Learn how to build a project.</a></p>
                <p class="subHeadThree steps"><a class="hpLink" href="https://osf.io/explore/activity/">Get inspired.</a></p>
            </div>
            <p class="stepsText">Want more than an answer to a quick question? Feel free to <a class="hpLink" href="mailto:contact@osf.io">email us</a> to schedule a help session or tutorial for you and your collaborators.<br>OSF is maintained by the non-profit <a class="hpLink" href="http://centerforopenscience.org/">Center for Open Science</a>.</p>
        </div>

    </div>

</%def>

<%def name="javascript_bottom()">

    ${parent.javascript_bottom()}

    <script type="text/javascript">
        $script(['/static/js/signUp.js']);
        $script.ready('signUp', function() {
            var signUp = new SignUp(
                '#signUpScope',
                '${api_url_for('register_user')}'
            );
        });
    </script>

</%def>