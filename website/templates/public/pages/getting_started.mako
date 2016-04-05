<%inherit file="base.mako"/>
<%def name="title()">Getting Started</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/getting-started-page.css">
</%def>

<%def name="content()">

    <div href="#start">
        <div class="col-sm-4 col-md-3 affix-parent scrollspy">
            <div data-spy="affix" data-offset-top="0" data-offset-bottom="250"  class="osf-affix gs-sidebar hidden-print hidden-xs panel panel-default" role="complementary">
                <ul class="nav nav-stacked nav-pills gs-sidenav" style="min-width: 205px">

                    <li>
                        <a  class="active" href="#start">Getting Started</a>
                        <ul class="nav">
                            <li><a href="#start-one"><i class="fa fa-chevron-right"></i> Creating a project</a></li>
                            <li><a href="#start-two"><i class="fa fa-chevron-right"></i> Collaboration</a></li>
                            <li><a href="#start-three"><i class="fa fa-chevron-right"></i> Version control</a></li>
                        </ul>
                    </li>
                    <li>
                        <a href="#structure">Structure</a>
                        <ul class="nav">
                            <li><a href="#organizer"><i class="fa fa-chevron-right"></i> Project organizer</a></li>
                            <li><a href="#dashboards"><i class="fa fa-chevron-right"></i> Dashboard</a></li>
                            <li><a href="#userprofile"><i class="fa fa-chevron-right"></i> User profile</a></li>
                            <li><a href="#projects"><i class="fa fa-chevron-right"></i> Projects</a></li>
                            <li><a href="#components"><i class="fa fa-chevron-right"></i> Components</a></li>
                            <li><a href="#files"><i class="fa fa-chevron-right"></i> Files</a></li>
                            <li><a href="#links"><i class="fa fa-chevron-right"></i> Links</a></li>
                            <li><a href="#forks"><i class="fa fa-chevron-right"></i> Forks</a></li>
                            <li><a href="#registrations"><i class="fa fa-chevron-right"></i> Registrations</a></li>
                            <li><a href="#wiki"><i class="fa fa-chevron-right"></i> Collaborative Wiki</a></li>
                        </ul>
                    </li>
                    <li>
                        <a href="#sharing">Sharing</a>
                        <ul class="nav">
                            <li><a href="#contributors"><i class="fa fa-chevron-right"></i> Contributors</a></li>
                            <li><a href="#privacy"><i class="fa fa-chevron-right"></i> Privacy</a></li>
                            <li><a href="#licenses"><i class="fa fa-chevron-right"></i> Licenses</a></li>
                            <li><a href="#citations"><i class="fa fa-chevron-right"></i> Citations</a></li>
                            <li><a href="#viewonly"><i class="fa fa-chevron-right"></i> View-only links</a></li>
                            <li><a href="#comments"><i class="fa fa-chevron-right"></i> Comments</a></li>
                        </ul>
                    </li>
                    <li>
                        <a href="#addons">Add-ons</a>
                        <ul class="nav">
                            <li><a href="#dropbox"><i class="fa fa-chevron-right"></i> Dropbox</a></li>
                            <li><a href="#github"><i class="fa fa-chevron-right"></i> GitHub</a></li>
                            <li><a href="#amazon"><i class="fa fa-chevron-right"></i> Amazon S3</a></li>
                            <li><a href="#figshare"><i class="fa fa-chevron-right"></i> figshare</a></li>
                            <li><a href="#dataverse"><i class="fa fa-chevron-right"></i> Dataverse</a></li>
                            <li><a href="#box"><i class="fa fa-chevron-right"></i> Box </a></li>
                            <li><a href="#drive"><i class="fa fa-chevron-right"></i> Google Drive</a></li>
                            <li><a href="#mendeley"><i class="fa fa-chevron-right"></i> Mendeley</a></li>
                            <li><a href="#zotero"><i class="fa fa-chevron-right"></i> Zotero</a></li>
                            <li><a href="#twofactor"><i class="fa fa-chevron-right"></i> Two-factor authentication</a></li>
                        </ul>
                    </li>
                    <li>
                        <a href="#metrics">Metrics</a>
                        <ul class="nav">

                            <li><a href="#statistics"><i class="fa fa-chevron-right"></i> Analytics</a></li>
                            <li><a href="#notifications"><i class="fa fa-chevron-right"></i> Notifications</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    <div class="col-sm-8 col-md-9">

        <div  id="start" class="p-t-xl">
            <h1 class="text-center">Getting Started with the OSF</h1>

            <p>The OSF has many tools to help you organize your research and communicate efficiently with your collaborators.
                Here, you can get the basics down, or learn the intricacies of each feature.</p>

            <div id="start-one" style="margin-top: 25px">
                <h3 class="text-center anchor">Use projects to organize your work</h3>
                <p>The OSF organizes your lines of research into projects. Projects come with features meant to streamline
                your workflow as well as make your work more discoverable.</p>
                <div class="row">
                    <div class="col-md-10 col-md-offset-1">
                        <div class="gs-video embed-responsive embed-responsive-16by9" style="max-width: 102%; width: 102%;">
    ##                        Max width for this video adjusted because of black border
                            <div class="embed-responsive-item youtube-loader" id="2TV21gOzfhw"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div id="start-two">
                <h3 class="text-center anchor">Collaborate with your colleagues</h3>
                <p>Keep yourself and your collaborators on point while collecting data by using the OSF. Add
                    contributors to your project so that everyone has access to the same files. Use our pre-formatted
                    citations and URLs to make sure credit is given where credit is due.  </p>
                <div class="row">
                    <div class="col-md-10 col-md-offset-1">
                        <div class="gs-video embed-responsive embed-responsive-16by9">
                            <div class="embed-responsive-item youtube-loader" id="UtahdT9wZ1Y"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div id="start-three">
                <h3 class="text-center anchor">Simplify your life with version control</h3>
                <p>Keep your research up to date by uploading new versions of documents to the OSF. We use version
                    control to keep track of older versions of your documents so you don't have to. You can also register
                    your work to freeze a version of your project.</p>
                <div class="row">
                    <div class="col-md-10 col-md-offset-1">
                        <div class="gs-video embed-responsive embed-responsive-16by9">
                            <div class="embed-responsive-item youtube-loader" id="ZUtazJQUwEc"></div>
                        </div>
                    </div>
                </div>
            </div>
        <div  id="structure" class="row p-t-xl">
            <h2 class="text-center">Structuring your work</h2>
            <div class="col-md-12">
                <%include file="/public/pages/help/organizer.mako"/>
                <%include file="/public/pages/help/dashboards.mako"/>
                <%include file="/public/pages/help/user_profile.mako"/>
                <%include file="/public/pages/help/projects.mako"/>
                <%include file="/public/pages/help/components.mako"/>
                <%include file="/public/pages/help/files.mako"/>
                <%include file="/public/pages/help/links.mako"/>
                <%include file="/public/pages/help/forks.mako"/>
                <%include file="/public/pages/help/registrations.mako"/>
                <%include file="/public/pages/help/wiki.mako"/>
            </div>
        </div>

        <div id="sharing" class="row p-t-xl">
            <h2 class="text-center">Sharing your work</h2>
            <div class="col-md-12">
                <%include file="/public/pages/help/contributors.mako"/>
                <%include file="/public/pages/help/privacy.mako"/>
                <%include file="/public/pages/help/licenses.mako"/>
                <%include file="/public/pages/help/citations.mako"/>
                <%include file="/public/pages/help/view_only.mako"/>
                <%include file="/public/pages/help/comments.mako"/>
            </div>
        </div>

        <div id="addons" class="row p-t-xl">
            <h3 class="m-t-lg">OSF Add-ons</h3>
            <div class="support-item">
                <h5 class="support-head f-w-xl">About Add-ons </h5>
                <div class="support-body">
                    <p>An add-on is a connection between the OSF to another tool such as Google Drive or GitHub.</p>
                    <p>You can connect an add-on from a project's "Settings" page.  Select the add-on to connect to your project.
                        In the "Configure Add-ons" section of the page, click "Connect Account" and log in to the third-party service,
                        if necessary. Once connected, you will be sent back to the "Settings" page, where you can choose what
                        you want to share.</p>
                </div>
            </div>

            <h4 class="m-t-lg">Storage add-ons</h4>
            <%include file="/public/pages/help/addons/dropbox.mako"/>
            <%include file="/public/pages/help/addons/github.mako"/>
            <%include file="/public/pages/help/addons/amazons3.mako"/>
            <%include file="/public/pages/help/addons/figshare.mako"/>
            <%include file="/public/pages/help/addons/dataverse.mako"/>
            <%include file="/public/pages/help/addons/box.mako"/>
            <%include file="/public/pages/help/addons/drive.mako"/>
            <h4 class="m-t-lg">Citation manager add-ons</h4>
            <%include file="/public/pages/help/addons/mendeley.mako"/>
            <%include file="/public/pages/help/addons/zotero.mako"/>
            <h4 class="m-t-lg">Security add-ons</h4>
            <%include file="/public/pages/help/addons/two-factor.mako"/>
        </div>

        <div id="metrics" class="row p-t-xl">
            <h2 class="text-center">Metrics</h2>
            <div class="col-md-12">
                <%include file="/public/pages/help/statistics.mako"/>
                <%include file="/public/pages/help/notifications.mako"/>
            </div>
        </div>
    </div>
</div>

<script type="text/javascript" src="/static/vendor/youtube/youtube-loader.js"></script>
</%def>
