<%inherit file="base.mako"/>

<%def name="title()">Home</%def>

<%def name="content_wrap()">
    <div class="watermarked">
            % if status:
                <div id="alert-container">
                % for message, css_class, dismissible in status:
                      <div class='alert alert-block alert-${css_class} fade in alert-front text-center'>
                        % if dismissible:
                        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                          <span aria-hidden="true">&times;</span>
                        </button>
                        % endif
                        <p>${message}</p>
                      </div>
                % endfor
                </div>
            % endif
            ${self.content()}
    </div><!-- end watermarked -->
</%def>

<%def name="content()">

    <!-- Main jumbotron for a primary marketing message or call to action -->
    <div id="home-hero">
      <div class="container text-center">
        <h1><strong>Simplified</strong> scientific collaboration</h1>
        <h3>Powerful end-to-end support for your research.</h3>

        <canvas id="demo-canvas"></canvas>

        <div id="logo" class="off">
          <div class="circle" id="circle-1"><span></span></div>
          <div class="circle" id="circle-2"><span></span></div>
          <div class="circle" id="circle-3"><span></span></div>
          <div class="circle" id="circle-4"><span></span></div>
          <div class="circle" id="circle-5"><span></span></div>
          <div class="circle" id="circle-6"><span></span></div>
          <div class="circle" id="circle-7"><span></span></div>
          <div class="circle" id="circle-8"><span></span></div>
        </div>

        <div id="hero-signup" class="container">
          <div class="row">
            <div class="col-sm-6 hidden-xs">
              <a class="youtube" href="//www.youtube.com/watch?v=2TV21gOzfhw"><i class="icon icon-play"></i></a>
              <img src="/static/img/front-page/screenshot.png" class="img-responsive" id="screenshot" alt="" />
            </div>
            <div class="col-sm-6">
              <h2>Free. Get started today.</h2>

             <div id="signUp" class="anchor"></div>
                <div id="signUpScope">
                    <form data-bind="submit: submit">
                        <div class="form-group" data-bind="css: {'has-error': fullName() && !fullName.isValid(), 'has-success': fullName() && fullName.isValid()}">
                              <label class="placeholder-replace" style="display:none">Full Name</label>
                              <input class="form-control" placeholder="Full Name" data-bind=" value: fullName, disable: submitted(), event: { blur: trim.bind($data, fullName)}">
                              <p class="help-block signup-help" data-bind="validationMessage: fullName" style="display: none;"></p>
                          </div>
                          <div class="form-group" data-bind="css: {'has-error': email1() && !email1.isValid(), 'has-success': email1() && email1.isValid()}">
                              <label class="placeholder-replace" style="display:none">Contact Email</label>
                              <input class="form-control" placeholder="Contact Email" data-bind=" value: email1, disable: submitted(), event: { blur: trim.bind($data, email1)}">
                              <p class="help-block signup-help" data-bind="validationMessage: email1" style="display: none;"></p>
                          </div>
                          <div class="form-group" data-bind="css: {'has-error': email2() && !email2.isValid(),'has-success': email2() && email2.isValid()}">
                              <label class="placeholder-replace" style="display:none">Confirm Email</label>
                              <input class="form-control" placeholder="Confirm Email" data-bind="value: email2, disable: submitted(), event: { blur: trim.bind($data, email2)}">
                              <p class="help-block signup-help" data-bind="validationMessage: email2" style="display: none;"></p>
                          </div>
                          <div class="form-group" data-bind="css: {'has-error': password() && !password.isValid(), 'has-success': password() && password.isValid()}">
                              <label class="placeholder-replace" style="display:none">Password</label>
                              <input type="password" class="form-control" placeholder="Password (Must be 6 to 35 characters)" data-bind=" value: password, disable: submitted(), event: {blur: trim.bind($data, password)}">
                                <p class="help-block signup-help" data-bind="validationMessage: password" style="display: none;"></p>
                          </div>

                          <!-- Flashed Messages -->
                          <div class="help-block signup-help" >
                              <p data-bind="html: flashMessage, attr.class: flashMessageClass" class=""></p>
                          </div>
                          <div>
                              <button type="submit" class="btn btn-warning" data-bind="visible: !submitted()" id="signupSubmit">Sign up free</button>
                          </div>
                  </form>

                </div><!-- end #signUpScope -->


            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="container grey-pullout space-top space-bottom">

      <div class="row space-bottom">
        <div class="col-xs-12 text-center">
          <h2><strong>Open Science Framework</strong></h2>
          <h3>Cloud-based management for your projects.</h3>
        </div>
      </div>

      <div class="row feature-1">
        <div class="col-md-6">
          <div class="row">
            <div class="col-xs-1">
              <i class="icon icon-cloud"></i>
            </div>
            <div class="col-xs-9 col-xs-offset-1">
              <h3>Structured projects</h3>
              <p>Keep all your files, data, and protocols in <strong>one centralized location.</strong> No more trawling emails to find files or scrambling to recover from lost data. <span class="label label-primary">Secure Cloud</span></p>
            </div>
          </div>
          <div class="row">
            <div class="col-xs-1">
              <i class="icon icon-group"></i>
            </div>
            <div class="col-xs-9 col-xs-offset-1">
              <h3>Control access</h3>
              <p><strong>You control which parts of your project are public or private</strong> making it easy to collaborate with the worldwide community or just your team.  <span class="label label-primary">Project-level Permissions</span></p>
            </div>
          </div>
          <div class="row">
            <div class="col-xs-1">
              <i class="icon icon-workflow"></i>
            </div>
            <div class="col-xs-9 col-xs-offset-1">
              <h3>Respect for your workflow</h3>
              <p><strong>Connect your favorite third party services</strong> directly to Open Science Framework.  <span class="label label-primary">3rd Party Integrations</span></p>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="student-image">
            <div class="quote">
              <span class="main">“The OSF is a great way to collaborate and stay organized while still using your favorite external services."</span>
              <span class="attrib"><strong>Kara Woo</strong> - Information Manager, Aquatic Ecology, Washington State</span>
            </div>
          </div>
        </div>
      </div>

    </div>

    <div class="container">
      <div class="feature-2 space-top space-bottom">
        <div class="row">
          <div class="col-xs-12 text-center headline">
            <h2>OSF Integrations make your <strong>workflow more efficient</strong></h2>
          </div>
        </div>
        <div class="row integrations">
          <div class="col-sm-3 col-xs-6">
            <img src="/static/img/front-page/dropbox.png" class="img-responsive"/>
          </div>
          <div class="col-sm-3 col-xs-6">
            <img src="/static/img/front-page/github.png" class="img-responsive"/>
          </div>
          <div class="col-sm-3 col-xs-6">
            <img src="/static/img/front-page/amazon.png" class="img-responsive"/>
          </div>
          <div class="col-sm-3 col-xs-6">
            <img src="/static/img/front-page/box.png" class="img-responsive"/>
          </div>
      </div>
      <div class="row integrations">
          <div class="col-sm-3 col-xs-6">
           <img src="/static/img/front-page/google.png" class="img-responsive"/>
          </div>
          <div class="col-sm-3 col-xs-6">
            <img src="/static/img/front-page/figshare.png" class="img-responsive"/>
          </div>
          <div class="col-sm-3 col-xs-6">
            <img src="/static/img/front-page/dataverse.png" class="img-responsive"/>
          </div>
          <div class="col-sm-3 col-xs-6">
            <img src="/static/img/front-page/mendeley.png" class="img-responsive"/>
          </div>
      </div>

      </div>
    </div>

    <div class="feature-3">
      <div class="container">
        <div class="row space-top">

          <div class="col-md-12 text-center space-bottom">
            <h2><strong>Everything</strong> your research needs to be a success</h2>
          </div>
        </div>
        <div class="row space-bottom">
          <div class="col-sm-6 text-right">
            <h3>Manage your project</h3>
            <p>View all of your projects from <strong>one dashboard.</strong></p>

            <h3>Quickly share files</h3>
            <p><strong>Share key project information</strong> and allow others to use and cite it.</p>

            <h3>See project changes</h3>
            <p>See the latest project changes, who is contributing and <strong>historical file versions.</strong></p>

            <h3>View project statistics</h3>
            <p>Access <strong>project data</strong> ranging from visits over time to top referring websites.</p>

          </div>

          <div class="col-sm-6 text-left">
            <h3>Archive your data</h3>
            <p>Computer or collaborator explode? With OSF <strong>you will never lose your project data.</strong></p>

            <h3>Control access and collaboration</h3>
            <p> Add others to your projects to collaborate, or provide private access to view.</p>

            <h3>Supercharge your workflow</h3>
            <p>OSF helps individuals, teams and labs make their <strong>research processes more efficient.</strong></p>

            <h3>Registration</h3>
            <p><strong>Preserve the state of a project at important parts of its lifecycle</strong> such as the onset of data collection.</p>
          </div>
        </div>
      </div>
    </div>

      <div class="feature-4">
        <div class="container">
          <div class="row space-top space-bottom text-center">
            <div class="col-md-4 col-md-offset-1">
              <i class="icon icon-earth"></i>
              <h2><strong>Contribute</strong> to global scientific efforts</h2>
              <p>Labs and teams across the globe use Open Science Framework to open their projects up to the scientific community. You can browse the newest and most popular public projects <a href="/explore/activity/">right here</a>. <span class="label label-warning">Get involved</span></p>
            </div>
            <div class="col-md-4 col-md-offset-1">
              <i class="icon icon-nonprofit"></i>
              <h2>We are a <strong>mission-driven non-profit</strong></h2>
              <p>OSF is a free, open-source service of the <a href="https://cos.io/">Center for Open Science</a>. We’re aligning scientific practices with scientific values by improving openness, integrity and reproducibility of research. <span class="label label-success">Non-Profit</span></p>
            </div>
          </div>
        </div>
      </div>

    <div class="container">

      <div class="space-top space-bottom feature-5">

        <div class="row">
          <div class="col-md-12 text-center">
            <h2><strong>Teachers, researchers, and global teams rely</strong> on the Open Science Framework</h2>
          </div>
        </div>

        <div class="row">
          <div class="col-xs-3">
            <img src="/static/img/front-page/user2.jpg" class="img-circle img-responsive" alt="Richard Ball" />
          </div>
          <div class="col-xs-8">
            <h3>Making research reproducible &amp; verifiable</h3>
            <p>OSF helps our students understand and apply sound data management principles to their work. And since we have easy access to all of the files the students are working with, it greatly enhances our ability to offer them constructive guidance.<br/><small><em>Richard Ball, Professor of Economics, Haverford College</em></small></em></small></p>
          </div>
        </div>

        <div class="row hidden-xs hidden-sm">
          <div class="col-md-7 col-md-offset-2">
            <h3>Version control makes life easier</h3>
            <p>The OSF makes version control effortless. My PI, my lab mates, and I have access to previous versions of a file at any time - and the most current version is always readily available.<br/><small><em>Erica Baranski, PhD Student, Social and Personality Psychology Funder Lab, UC Riverside</em></small></em></small></p>
          </div>
          <div class="col-md-3">
            <img src="/static/img/front-page/user3.jpg" class="img-circle img-responsive" alt="Erica Baranski" />
          </div>
        </div>

        <div class="row hidden-xs hidden-sm">
          <div class="col-md-3">
            <img src="/static/img/front-page/user4.jpg" class="img-circle img-responsive" alt="" />
          </div>
          <div class="col-md-7">
            <h3>A centralized hub of information</h3>
            <p>The OSF creates a centralized hub of information where I can oversee a diversity of research projects across multiple classes. The centralization, organization and anywhere-access save me the time and energy necessary for managing these projects.<br/><small><em>Anne Allison, Associate Professor of Biology at Piedmont Virginia Community College</em></small></em></small></p>
          </div>
        </div>


      </div>
    </div>
    <div class="space-top space-bottom feature-6">
      <div class="container">
        <div class="row">
          <div class="col-md-8">
            <h2><strong>Free and open source.</strong></h2>
            <h4>OSF is a public good built to support your research.</h4>
            <a href="#" class="btn btn-info btn-lg">Get Started</a>
          </div>
          <div class="col-md-4 hidden-xs hidden-sm">
            <div id="logo">
              <div class="circle" id="circle-1"><span></span></div>
              <div class="circle" id="circle-2"><span></span></div>
              <div class="circle" id="circle-3"><span></span></div>
              <div class="circle" id="circle-4"><span></span></div>
              <div class="circle" id="circle-5"><span></span></div>
              <div class="circle" id="circle-6"><span></span></div>
              <div class="circle" id="circle-7"><span></span></div>
              <div class="circle" id="circle-8"><span></span></div>
            </div>
          </div>
        </div>
      </div>

    </div>


</%def>

<%def name="footer()">

</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src=${"/static/public/js/home-page.js" | webpack_asset}></script>
</%def>

