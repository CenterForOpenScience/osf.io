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
        <div class="container osf-meeting-header">
            <div class="text-center m-b-60">
                <h1>OSF for Meetings</h1>
                <h3>A <strong>free poster and presentation sharing service</strong> for academic meetings and conferences.</h3>
            </div>
            <div class="row">
                <div class="col-sm-6 text-center m-b-60" >
                    <h3> For Conference Organizers </h3>
                    <i class="fa fa-rocket fa-custom-8x"></i>
                    <div class="p-h-lg text-left">
                        <h4 class="text-justify m-v-15-p">Reigster your conference and get an easy submission process, a permanent link to your presentations, plus analytics about who has viewed and downloaded your work.</h4></div>
                    <div class="p-h-xl p-v-md">
                        <button class="btn btn-success btn-lg" type="button" data-toggle="collapse" data-target="#osf-meeting-register" aria-expanded="false" aria-controls="collapseExample">
                            Reigster
                        </button>
                    </div>
                    <div class="collapse" id="osf-meeting-register">
                        <div class="well m-h-lg osf-box-lt box-round text-left m-v-15-p">
                            <p>The OSF can host posters and talks for scholarly meetings. Submitting a presentation is easy—<strong>JUST send an email to the conference address</strong>, and we'll create an OSF project for you. You'll get a permanent link to your presentation, plus analytics about who has viewed and downloaded your work.</p>
                            <p>OSF for Meetings is a product that we offer to academic conferences at no cost. To request poster and talk hosting for a conference, <strong>email us at contact@cos.io</strong>. We'll review and add your conference within one business day.</p>
                        </div>
                    </div>
                </div>
                <div class="col-sm-6 text-center m-b-lg">
                    <h3> For Conference Participants </h3>
                    <i class="fa fa-cloud-upload fa-custom-8x"></i>
                    <div class="p-h-xl text-left">
                        <h4 class="text-justify m-v-15-p">Share your posters and papers and use the Open Science Framework to upload your slides and other supporting materials.</h4></div>
                    <div class="p-h-xl p-v-md">
                        <button class="btn btn-success btn-lg" type="button" data-toggle="collapse" data-target="#osf-meeting-upload" aria-expanded="false" aria-controls="collapseExample">
                            Upload
                        </button>
                    </div>
                    <div class="collapse" id="osf-meeting-upload">
                        <div class="well m-h-lg osf-box-lt box-round text-left m-v-15-p">
                            <p>The OSF can host posters and talks for scholarly meetings. Submitting a presentation is easy—<strong>JUST send an email to the conference address</strong>, and we'll create an OSF project for you. You'll get a permanent link to your presentation, plus analytics about who has viewed and downloaded your work.</p>
                            <p>OSF for Meetings is a product that we offer to academic conferences at no cost. To request poster and talk hosting for a conference, email us at contact@cos.io. We'll review and add your conference within one business day.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="container">
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
                                <small>Only conferences with at least five submissions are displayed here.</small>
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
                <div class="osf-box-lt box-round p-v-md m-t-xl m-h-md">
                    <i class="fa fa-eye fa-custom-7x blue-icon"></i>
                    <h3>Discover</h3>
                    <div class="p-h-lg">
                        <p class="osf-meeting-p">Wish you had a widely-known place for people to learn from your talk and/or poster, then you have found your answer.</p></div>
                </div>
            </div>
            <div class="col-md-4 col-sm-4 text-center">
                <div class="osf-box-lt box-round p-v-md  m-t-xl m-h-md">
                    <i class="fa fa-users fa-custom-7x blue-icon"></i>
                    <h3>Share</h3>
                    <div class="p-h-lg">
                        <p class="osf-meeting-p">OSF has increased accessibility and collaboration for researchers like no other platform… it is truly the first of it’s kind.</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4 col-sm-4 text-center">
                <div class="osf-box-lt box-round p-v-md  m-t-xl m-h-md">
                    <i class="fa fa-thumbs-up fa-custom-7x blue-icon"></i>
                    <h3>Trust</h3>
                    <div class="p-h-lg">
                        <p class="osf-meeting-p">OSF for Meetings is a trusted partner for over XX academic conferences. </p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row text-center">
            <h1> Who uses OSF for Meetings?</h1>
        </div>
        <div class="row org-logo m-b-60">
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
