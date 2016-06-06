<%inherit file="base.mako"/>

<%def name="title()">Preprints</%def>
<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/preprint-landing-page.css">
    <link rel="stylesheet" href="/static/css/pages/landing-page.css">
</%def>

<%def name="content_wrap()">
    <div class="watermarked">
            % if status:
                <%include file="alert.mako" args="extra_css='alert-front text-center'"/>
            % endif
            ${self.content()}
    </div><!-- end watermarked -->
</%def>

<%def name="content()">
    <div class="osf-meeting-header-img">
        <div class="osf-meeting-header">
            <div class="container ">
                <div class="text-center m-b-lg">
                    <h1 class="osf-preprint-lead">OSF Preprints</h1>
                    <h2 class="osf-preprint-subheading">Coming Soon</h2>
                </div>
                <div class="network-img" style="height: 700px; margin-bottom: -700px;"> </div>
                <div class="row">
                    <div class="col-md-6 col-lg-5 col-xl-4 text-center m-b-lg preprint-feature" >
                        <i class="fa fa-search m-v-sm" style="padding-top: 10px;"></i>
                        <h3 class="f-w-xl">Share and discover research as it happens</h3>
                    </div>
                    <div class="col-md-6 col-lg-5 col-lg-offset-2 col-xl-4 col-xl-offset-4 text-center m-b-lg preprint-feature">
                        <i class="fa fa-users m-v-sm" style="padding-top: 30px;"></i>
                        <h3 class="f-w-xl">Receive quick feedback on your research</h3>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6 col-lg-5 col-xl-4 text-center m-b-lg preprint-feature" >
                        <i class="fa fa-cloud-upload m-v-sm" style="padding-top: 20px;"></i>
                        <h3 class="f-w-xl">Deposit and search via <a href="https://osf.io ">OSF</a></h3>
                    </div>
                    <div class="col-md-6 col-lg-5 col-lg-offset-2 col-xl-4 col-xl-offset-4 text-center m-b-lg preprint-feature">
                        <i class="fa fa-cubes m-v-sm" style="padding-top: 15px; padding-left: 7px;"></i>
                        <h3 class="f-w-xl">Aggregate across preprint services via <a href="https://osf.io/share/">SHARE</a></h3>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="space-top space-bottom feature-6 grey-background" style="">
      <div class="container">
        <div class="row">
          <div class="col-md-7">
            <h2><strong>Tools for communities</strong></h2>
            <h4> Create your own branded preprint servers backed by the OSF.</h4>
            ## <a href="mailto:contact@osf.io" class="btn btn-info btn-lg">Contact us</a>

            ${mailchimp_form()}
          </div>
          <div class="col-md-5 hidden-xs hidden-sm">
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


<%def name="mailchimp_form()">
<!-- Begin MailChimp Signup Form -->
<div id="mc_embed_signup">
<form action="//centerforopenscience.us9.list-manage.com/subscribe/post?u=4ea2d63bcf7c2776e53a62167&amp;id=9acfb7c169" method="post" id="mc-embedded-subscribe-form" name="mc-embedded-subscribe-form" class="validate" target="_blank" novalidate>
    <div id="mc_embed_signup_scroll">

<div class="form-group mc-field-group">
  <label for="mce-EMAIL">Email Address  <span class="asterisk">*</span></label>
  <input type="email" value="" placeholder="Required" name="EMAIL" class="form-control required email" id="mce-EMAIL">
</div>
<div class="form-group mc-field-group">
  <label for="mce-FNAME">First Name </label>
  <input type="text" value="" name="FNAME" placeholder="Optional" class="form-control" id="mce-FNAME">
</div>
<div class="form-group mc-field-group">
  <label for="mce-LNAME">Last Name </label>
  <input type="text" value="" name="LNAME" placeholder="Optional" class="form-control" id="mce-LNAME">
</div>
  <div id="mce-responses" class="clear">
    <div class="response" id="mce-error-response" style="display:none"></div>
    <div class="response" id="mce-success-response" style="display:none"></div>
  </div>    <!-- real people should not fill this in and expect good things - do not remove this or risk form bot signups-->
    <div style="position: absolute; left: -5000px;" aria-hidden="true"><input type="text" name="b_4ea2d63bcf7c2776e53a62167_9acfb7c169" tabindex="-1" value=""></div>
    ## <div class="clear">
    <input type="submit" value="Sign up for updates" name="subscribe" id="mc-embedded-subscribe" class="btn btn-primary btn-large button"></div>
    ## </div>
</form>
</div>
<!--End mc_embed_signup-->
</%def>
