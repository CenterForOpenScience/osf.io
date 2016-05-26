<%inherit file="base.mako"/>
<%def name="title()">Settings</%def>
<%def name="content()">
<% from website import settings %>
<h2 class="page-header">Settings
    <div class="pull-right">
        <a href="/profile" class="btn btn-link"><i class="fa fa-user m-r-sm"></i>View your profile </a>
    </div>
</h2>

## TODO: Review and un-comment
##<div class="row">
##    <div class="col-sm-6">
##        <div class="panel panel-default">
##            <div class="panel-heading"><h3 class="panel-title">Merge Accounts</h3></div>
##            <div class="panel-body">
##                <a href="/user/merge/">Merge with duplicate account</a>
##            </div>
##        </div>
##    </div>
##</div>

<div id="profileSettings" class="row">

    <div class="col-sm-3 affix-parent">
      <%include file="include/profile/settings_navpanel.mako" args="current_page='profile'"/>
    </div>

    <div class="col-sm-9 col-md-7">

        <div id="userProfile">

            <ul class="nav nav-tabs">
                <li class="active"><a href="#names" data-toggle="tab">Name</a></li>
                <li><a href="#social" data-toggle="tab">Social</a></li>
                <li><a href="#jobs" data-toggle="tab">Employment</a></li>
                <li><a href="#schools" data-toggle="tab">Education</a></li>
            </ul>

            <div class="tab-content" id="containDrag">
                <div class="m-t-md tab-pane active" id="names">
                    <div data-bind="template: {name: 'profileName'}"></div>
                </div>
                <div class="m-t-md tab-pane" id="social">
                    <div data-bind="template: {name: 'profileSocial'}"></div>
                </div>
                <div class="m-t-md tab-pane" id="jobs">
                    <div data-bind="template: {name: 'profileJobs'}"></div>
                </div>
                <div class="m-t-md tab-pane" id="schools">
                    <div data-bind="template: {name: 'profileSchools'}"></div>
                </div>
            </div>

        </div>

    </div>

</div>

## TODO: Review and un-comment
##<div mod-meta='{
##        "tpl": "util/render_keys.mako",
##        "uri": "/api/v1/settings/keys/",
##        "replace": true,
##        "kwargs" : {
##            "route": "/settings/"}
##        }'></div>

<%include file="include/profile/names.mako" />
<%include file="include/profile/social.mako" />
<%include file="include/profile/jobs.mako" />
<%include file="include/profile/schools.mako" />
</%def>

<%def name="javascript_bottom()">
<script type="text/javascript">
    ## Store mako variables on window so they are accessible from JS
    ## modules. Not sure if this is a good idea.
    window.contextVars = window.contextVars || {};
    window.contextVars.nameUrls = {
        crud: ${ api_url_for('serialize_names') | sjson, n },
        impute: ${ api_url_for('impute_names') | sjson, n }
    };
    window.contextVars.socialUrls = {
        crud: ${ api_url_for('serialize_social') | sjson, n }
    };
    window.contextVars.jobsUrls = {
        crud: ${ api_url_for('serialize_jobs') | sjson, n }
    };
    window.contextVars.schoolsUrls = {
        crud: ${ api_url_for('serialize_schools') | sjson, n }
    };
</script>
<script src=${"/static/public/js/profile-settings-page.js" | webpack_asset}></script>
</%def>
