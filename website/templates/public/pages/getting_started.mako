<%inherit file="base.mako"/>
<%def name="title()">Getting Started</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/getting-started-page.css">
</%def>

<%def name="content()">
 <!-- Getting Started -->
 <div class="row">
    <div class="col-xs-12 col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2">
          <h2 class="m-t-xl m-b-lg"> Getting Started with OSF </h2>
            <div class="support-item">
                <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> Use projects to organize your work</h5>
                <div class="support-body">The OSF organizes your lines of research into projects. Projects come with features meant to streamline
                your workflow as well as make your work more discoverable.
                <div class="row">
                        <div class="col-md-10 col-md-offset-1">
                            <div class="gs-video embed-responsive embed-responsive-16by9" style="max-width: 102%; width: 102%;">
                                   <!-- Max width for this video adjusted because of black border -->
                                <div class="embed-responsive-item youtube-loader" id="2TV21gOzfhw"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>


            <div class="support-item">
                <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i>Collaborate with your colleagues  </h5>
                <div class="support-body">
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
            </div>

            <div class="support-item">
                <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> Simplify your life with version control </h5>
                <div class="support-body">
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
            </div>

            <h3 class="m-t-lg">Structuring your work</h3>
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

            <h3 class="m-t-lg">Sharing your work</h3>
            <%include file="/public/pages/help/contributors.mako"/>
            <%include file="/public/pages/help/privacy.mako"/>
            <%include file="/public/pages/help/licenses.mako"/>
            <%include file="/public/pages/help/citations.mako"/>
            <%include file="/public/pages/help/view_only.mako"/>
            <%include file="/public/pages/help/comments.mako"/>

            <h3 class="m-t-lg">OSF Add-ons</h3>
            <div class="support-item">
                <h5 class="support-head f-w-xl"><i class="fa fa-angle-right"></i> About Add-ons </h5>
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

            <h3 class="m-t-lg">Metrics</h3>
            <%include file="/public/pages/help/statistics.mako"/>
            <%include file="/public/pages/help/notifications.mako"/>

    </div>
 </div>


<script type="text/javascript" src="/static/vendor/youtube/youtube-loader.js"></script>
</%def>