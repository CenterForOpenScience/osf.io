<%inherit file="base.mako"/>

<%def name="title()">Meetings</%def>
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
    <div class="osf-meeting-header-img">
        <div class="osf-meeting-header">
            <div class="container ">
                <div class="network-img"> </div>
            <div class="text-center m-b-40">
                <h1>OSF for Meetings</h1>
                <h3>A <strong>free poster and presentation sharing service</strong> for academic meetings and conferences.</h3>
            </div>
            <div class="row">
                <div class="col-md-6 col-lg-5 col-xl-4 text-center m-b-40" >
                    <i class="fa fa-users fa-custom-8x m-v-sm"></i>
                    <h3 class="f-w-xl"> For Conference Organizers </h3>
                    <div class="text-left">
                        <p class="osf-meeting-p">Register your conference and get an easy submission process, a permanent link to your presentations, plus analytics about who has viewed and downloaded your work.</p>
                    </div>
                    <div class="p-v-md">
                        <button class="btn btn-success btn-lg" type="button" data-toggle="collapse" data-target="#osf-meeting-register" aria-expanded="false" aria-controls="collapseExample">
                            Register
                        </button>
                    </div>
                    <div class="collapse" id="osf-meeting-register">
                        <div class="m-lg osf-box-lt p-md text-left">
                            <p>OSF for Meetings is a product that we offer to academic conferences at no cost. To request poster and talk hosting for a conference:</p>
                                <p class="text-center"><strong> JUST email us at <a href="mailto:contact@cos.io">contact@cos.io</a> </strong></p>
                             <p>We'll review and add your conference within one business day.</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 col-lg-5 col-lg-offset-2 col-xl-4 col-xl-offset-4 text-center m-b-40">
                    <i class="fa fa-cloud-upload fa-custom-8x m-v-sm"></i>
                    <h3 class="f-w-xl"> For Conference Participants </h3>
                    <div class="text-left">
                        <p class="osf-meeting-p">Share your posters and papers and use the Open Science Framework to upload your slides and other supporting materials.</p></div>
                    <div class="p-v-md">
                        <button class="btn btn-success btn-lg" type="button" data-toggle="collapse" data-target="#osf-meeting-upload" aria-expanded="false" aria-controls="collapseExample">
                            Upload
                        </button>
                    </div>
                    <div class="collapse" id="osf-meeting-upload">
                        <div class="m-lg osf-box-lt p-md text-left">
                            <p>The OSF can host posters and talks for scholarly meetings.
                                Submitting a presentation is easy.</p>
                            <p class="text-center"><strong> JUST send an email to the conference address.</strong></p>
                            <p>We'll create an OSF project for you. You'll get a permanent link to your presentation,
                                plus analytics about who has viewed and downloaded your work.</p>
                        </div>

                    </div>
                </div>
            </div>
        </div>
        </div>
    </div>

    <div class="container grey-background">
        <div class="row m-v-40">
            <div class="col-md-12">
                <div role="tabpanel">
                    <!-- Nav tabs -->
                    <ul class="nav nav-tabs m-b-md" role="tablist">
                        <li role="presentation" class="active">
                            <a href="#meetings" aria-controls="meetings" role="tab" data-toggle="tab">All Meetings</a>
                        </li>
                        <li role="presentation">
                            <a href="#submissions" aria-controls="submissions" role="tab" data-toggle="tab">All Submissions</a>
                        </li>
                    </ul>
                    <!-- Tab panes -->
                    <div class="tab-content">
                        <div role="tabpanel" class="tab-pane active" id="meetings">
                            <p>
                                <small>Only conferences with at least five submissions are displayed.</small>
                            </p>
                            <div id="meetings-grid"></div>
                        </div>
                        <div role="tabpanel" class="tab-pane" id="submissions">
                            <div id="submissions-grid"></div>
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <div class="row icon-bar m-v-40">
            <div class="col-md-4 col-sm-4 text-center ">
                <div class="p-v-md m-t-xl m-h-md">
                    <i class="fa fa-eye fa-custom-7x icon-circle blue-icon"></i>
                    <h3>Discover</h3>
                    <div class="p-h-lg">
                        <p class="osf-meeting-p">Wish you had a widely-known place for people to learn from your talk and/or poster, then you have found your answer.</p></div>
                </div>
            </div>
            <div class="col-md-4 col-sm-4 text-center">
                <div class=" p-v-md  m-t-xl m-h-md">
                    <i class="fa fa-share-alt fa-custom-7x icon-circle  blue-icon"></i>
                    <h3>Share</h3>
                    <div class="p-h-lg">
                        <p class="osf-meeting-p">OSF has increased accessibility and collaboration for researchers like no other platform… it is truly the first of it’s kind.</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4 col-sm-4 text-center">
                <div class="p-v-md  m-t-xl m-h-md">
                    <i class="fa fa-thumbs-up fa-custom-7x icon-circle blue-icon"></i>
                    <h3>Trust</h3>
                    <div class="p-h-lg">
                        <p class="osf-meeting-p">OSF for Meetings is a trusted partner for over XX academic conferences. </p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row text-center m-b-md">
            <h2> Who uses OSF for Meetings?</h2>
        </div>
        <div class="row org-logo m-b-40">
            <div class="col-sm-3 col-xs-6  text-center">
                <a href="http://www.psychologicalscience.org/"><img src="/static/img/meeting-page/APS.jpg" class="img-responsive"></a>
            </div>
            <div class="col-sm-3 col-xs-6 text-center">
                <a href="http://www.bitss.org/"><img src="/static/img/meeting-page/BITSS.png" class="img-responsive"></a>
            </div>
            <div class="col-sm-3 col-xs-6 text-center">
                <a href="http://www.nrao.edu/"><img src="/static/img/meeting-page/NRAO.jpg" class="img-responsive"></a>
            </div>
            <div class="col-sm-3 col-xs-6 text-center">
                <a href="http://www.spsp.org/"><img src="/static/img/meeting-page/SPSP.jpg" class="img-responsive"></a>
            </div>
        </div>
    </div>

</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = window.contextVars || {};
        window.contextVars.meetings = ${meetings | sjson, n};
        window.contextVars.submissions = ${submissions | sjson, n};
    </script>
    <script src=${"/static/public/js/meetings-page.js" | webpack_asset}></script>
</%def>
