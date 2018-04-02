<%inherit file="base.mako"/>

<%def name="title()">Meetings</%def>

<%def name="nav()">
    <%namespace name="nav_helper" file="nav.mako" />
    ${nav_helper.nav(service_name='MEETINGS', service_url='/meetings/', service_support_url='http://help.osf.io/m/meetings/')}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/meeting-landing-page.css">
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
    <div id="osfDonateBanner"></div>
    <div class="osf-meeting-header-img">
        <div class="osf-meeting-header">
            <div class="container ">
            <div class="text-center m-b-lg">
                <h1><img src="/static/img/meeting-page/osf_meetings_white.png" alt="Logo for OSF meeting" style="width: 80%"></h1>
                <h3>A <strong>free poster and presentation sharing service</strong> for academic meetings and conferences</h3>
            </div>
                <div class="network-img"> </div>
            <div class="row">
                <div class="col-md-6 col-lg-5 col-xl-4 text-center m-b-lg" >
                    <i class="fa fa-users m-v-sm"></i>
                    <h3 class="f-w-xl"> For Conference Organizers </h3>
                    <div class="text-left">
                        <p class="osf-meeting-p">Register your event to broaden its impact.  Events get a dedicated page, an easy submission process, and persistent links.</p>
                    </div>
                    <div class="p-v-md">
                        <button class="btn btn-success btn-lg" type="button" data-toggle="collapse" data-target="#osf-meeting-register" aria-expanded="false" aria-controls="collapseExample">
                            Register
                        </button>
                    </div>
                    <div class="collapse" id="osf-meeting-register">
                        <div class="m-lg osf-box-lt p-md text-left">
                            <p>OSF Meetings is a product that we offer to academic conferences at no cost. To request poster and talk hosting for a conference:</p>
                                <p class="text-center"><strong> Email us at <a href="mailto:${osf_contact_email}">${osf_contact_email}</a> </strong></p>
                             <p>We'll review and add your conference within one business day.</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 col-lg-5 col-lg-offset-2 col-xl-4 col-xl-offset-4 text-center m-b-lg">
                    <i class="fa fa-cloud-upload m-v-sm"></i>
                    <h3 class="f-w-xl"> For Conference Participants </h3>
                    <div class="text-left">
                        <p class="osf-meeting-p">Share your posters and presentations along with any supporting data and materials. Get persistent links and usage analytics.</p></div>
                    <div class="p-v-md">
                        <button class="btn btn-success btn-lg" type="button" data-toggle="collapse" data-target="#osf-meeting-upload" aria-expanded="false" aria-controls="collapseExample">
                            Upload
                        </button>
                    </div>
                    <div class="collapse" id="osf-meeting-upload">
                        <div class="m-lg osf-box-lt p-md text-left">
                            <p>The OSF can host posters and talks for scholarly meetings.
                                Submitting a presentation is easy:</p>

                            <ul>
                                <li>Find the email address for your conference by clicking on its name in the list below</li>
                                <li>Send your materials to the OSF Meetings email address for your conference</li>
                            </ul>

                            <p> We’ll create an OSF project for you. You'll get a permanent link to your presentation, plus analytics about who has viewed and downloaded your work.</p>
                        </div>

                    </div>
                </div>
            </div>
        </div>
        </div>
    </div>

    <div class="container grey-background">
        <div class="row m-v-lg">
            <div class="col-md-12">
                <div role="tabpanel">
                    <!-- Nav tabs -->
                    ## <ul class="nav nav-tabs m-b-md" role="tablist">
                    ##     <li role="presentation" class="active">
                    ##         <a href="#meetings" aria-controls="meetings" role="tab" data-toggle="tab">All meetings</a>
                    ##     </li>
                    ##     <li role="presentation">
                    ##         <a href="#submissions" aria-controls="submissions" role="tab" data-toggle="tab">All submissions</a>
                    ##     </li>
                    ## </ul>
                    <!-- Tab panes -->
                    <div class="tab-content">
                        <div role="tabpanel" class="tab-pane active" id="meetings">
                            <p>
                                <small>Only conferences with at least five submissions are displayed.</small>
                            </p>
                            <div id="meetings-grid"></div>
                        </div>
                        <div role="tabpanel" class="tab-pane" id="submissions">

                            <div id="submissions-grid">
                                <div id="allMeetingsLoader" class="spinner-loading-wrapper">
                                    <div class="ball-scale ball-scale-blue">
                                        <div></div>
                                    </div>
                                    <p class="m-t-sm fg-load-message"> Loading submissions...</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <div class="row icon-bar m-v-lg">
            <div class="col-md-4 col-sm-4 text-center ">
                <div class="p-v-md m-t-xl m-h-md">
                    <i class="fa fa-eye fa-custom-7x icon-circle blue-icon"></i>
                    <h3>Discover</h3>
                    <div class="p-h-lg">
                        <p class="osf-meeting-p">Explore posters and presentations from events long after they're over.</p></div>
                </div>
            </div>
            <div class="col-md-4 col-sm-4 text-center">
                <div class=" p-v-md  m-t-xl m-h-md">
                    <i class="fa fa-share-alt fa-custom-7x icon-circle  blue-icon"></i>
                    <h3>Share</h3>
                    <div class="p-h-lg">
                        <p class="osf-meeting-p">Get persistent links to your content and increase your impact.</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4 col-sm-4 text-center">
                <div class="p-v-md  m-t-xl m-h-md">
                    <i class="fa fa-magic fa-custom-7x icon-circle blue-icon"></i>
                    <h3>Enhance</h3>
                    <div class="p-h-lg">
                        <p class="osf-meeting-p">Add supplementary data and materials to your submission to make your work more transparent.</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row text-center m-b-md">
            <h2> Who uses OSF Meetings?</h2>
        </div>
        <div class="row org-logo m-b-lg">
            <div class="col-sm-3 col-xs-6  text-center">
                <a href="http://www.psychologicalscience.org/" target="_blank"><img src="/static/img/meeting-page/APS.jpg" alt="Logo for American Physiological Society (APS)" class="img-responsive"></a>
            </div>
            <div class="col-sm-3 col-xs-6 text-center">
                <a href="http://www.bitss.org/" target="_blank"><img src="/static/img/meeting-page/BITSS.png" alt="Logo for Berkeley Initiative for Transparency in the Social Sciences (BITSS)" class="img-responsive"></a>
            </div>
            <div class="col-sm-3 col-xs-6 text-center">
                <a href="http://www.nrao.edu/" target="_blank"><img src="/static/img/meeting-page/NRAO.jpg" alt="Logo for National Radio Astronomy Observatory (NRAO)" class="img-responsive"></a>
            </div>
            <div class="col-sm-3 col-xs-6 text-center">
                <a href="http://www.spsp.org/" target="_blank"><img src="/static/img/meeting-page/SPSP.jpg" alt="Logo for Society for Personality and Social Psychology (SPSP)" class="img-responsive"></a>
            </div>
        </div>
    </div>

</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = window.contextVars || {};
        window.contextVars.meetings = ${meetings | sjson, n};
    </script>
    <script src=${"/static/public/js/meetings-page.js" | webpack_asset}></script>
</%def>
