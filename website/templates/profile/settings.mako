<%inherit file="base.mako"/>
<%def name="title()">Settings</%def>
<%def name="content()">
<% from website import settings %>
<h2 class="page-header">Profile Information</h2>

## TODO: Review and un-comment
##<div class="row">
##    <div class="col-md-6">
##        <div class="panel panel-default">
##            <div class="panel-heading"><h3 class="panel-title">Merge Accounts</h3></div>
##            <div class="panel-body">
##                <a href="/user/merge/">Merge with duplicate account</a>
##            </div>
##        </div>
##    </div>
##</div>

<div class="row">

    <div class="col-md-3">
        <div class="panel panel-default">
            <ul class="nav nav-stacked nav-pills">
                <li><a href="#">Profile Information</a></li>
                <li><a href="${ web_url_for('user_account') }">Account Settings</a></li>
                <li><a href="${ web_url_for('user_addons') }">Configure Add-ons</a></li>
                %if settings.ENABLE_EMAIL_SUBSCRIPTIONS:
                    <li><a href="${ web_url_for('user_notifications') }">Notifications</a></li>
                %endif
            </ul>
        </div><!-- end sidebar -->
    </div>

    <div class="col-md-6">

        <div id="userProfile">

            <ul class="nav nav-tabs">
                <li class="active"><a href="#names" data-toggle="tab">Name</a></li>
                <li><a href="#social" data-toggle="tab">Social</a></li>
                <li><a href="#jobs" data-toggle="tab">Employment</a></li>
                <li><a href="#schools" data-toggle="tab">Education</a></li>
            </ul>

            <div class="tab-content">

                <div class="tab-pane active" id="names">
                    <div data-bind="template: {name: 'profileName'}"></div>
                </div>

                <div class="tab-pane" id="social">
                    <div data-bind="template: {name: 'profileSocial'}"></div>
                </div>

                <div class="tab-pane" id="jobs">
                    <div data-bind="template: {name: 'profileJobs'}"></div>
                </div>

                <div class="tab-pane" id="schools">
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
        crud: '${ api_url_for('serialize_names') }',
        impute: '${ api_url_for('impute_names') }'
    };
    window.contextVars.socialUrls = {
        crud: '${ api_url_for('serialize_social') }'
    };
    window.contextVars.jobsUrls = {
        crud: '${ api_url_for('serialize_jobs') }'
    };
    window.contextVars.schoolsUrls = {
        crud: '${ api_url_for('serialize_schools') }'
    };
</script>
<script src="/static/public/js/profile-settings-page.js"></script>
</%def>
