<%inherit file="base.mako"/>

<%def name="title()">Preprints</%def>
<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/preprint-landing-page.css">
    <link rel="stylesheet" href="/static/css/pages/landing-page.css">
    <link rel="stylesheet" href="/static/css/front-page.css">
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
                    <div class="network-img"> </div>
                <div class="row">
                    <div class="col-md-6 col-lg-5 col-xl-4 text-center m-b-lg preprint-feature" >
                        <i class="fa fa-search m-v-sm"></i>
                        <h3 class="f-w-xl">Share and discover research as it happens</h3>
                    </div>
                    <div class="col-md-6 col-lg-5 col-lg-offset-2 col-xl-4 col-xl-offset-4 text-center m-b-lg preprint-feature">
                        <i class="fa fa-users m-v-sm"></i>
                        <h3 class="f-w-xl">Receive quick feedback on your research</h3>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6 col-lg-5 col-xl-4 text-center m-b-lg preprint-feature" >
                        <i class="fa fa-cloud-upload m-v-sm"></i>
                        <h3 class="f-w-xl">Deposit and search via <a href="https://osf.io ">OSF</a></h3>
                    </div>
                    <div class="col-md-6 col-lg-5 col-lg-offset-2 col-xl-4 col-xl-offset-4 text-center m-b-lg preprint-feature">
                        <i class="fa fa-cubes m-v-sm"></i>
                        <h3 class="f-w-xl">Aggregate across preprint services via <a href="https://osf.io/share/">SHARE</a></h3>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="space-top space-bottom feature-6">
      <div class="container">
        <div class="row">
          <div class="col-md-8">
            <h2><strong>Tools for communities</strong></h2>
            <h4> Create your own branded preprint servers backed by the OSF.</h4>
            <a href="mailto:contact@osf.io" class="btn btn-info btn-lg">Contact us</a>
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
