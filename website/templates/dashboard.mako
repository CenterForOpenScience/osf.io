<%inherit file="base.mako"/>
<%def name="title()">Dashboard</%def>

<%def name="content()">
% if disk_saving_mode:
    <div class="alert alert-info"><strong>NOTICE: </strong>Forks, registrations, and uploads will be temporarily disabled while the OSF undergoes a hardware upgrade. These features will return shortly. Thank you for your patience.</div>
% endif
<div class="row">
    <div class="col-sm-7">
        <div>
          <h3>Projects </h3>
            <hr />
        </div><!-- end div -->

        <div class="project-organizer" id="projectOrganizerScope">
            <div id="project-grid">
                <div class="spinner-loading-wrapper">
                    <div class="logo-spin logo-lg"></div>
                     <p class="m-t-sm fg-load-message"> Loading projects...  </p>
                </div>
            </div>
        </div><!-- end project-organizer -->
    </div><!-- end col -->

    ## Knockout componenet templates
    <%include file="components/dashboard_templates.mako"/>
    <div class="col-sm-5">
        <div class="p-b-xs m-t-lg m-b-xs" id="obTabHead">
            <ul class="nav nav-tabs" role="tablist">
            <li class="active"><a href="#quicktasks" role="tab" data-toggle="tab">Quick tasks</a></li>
            <li><a href="#watchlist" role="tab" data-toggle="tab">Watchlist</a></li>
            ## %if 'badges' in addons_enabled:
            ## <li><a href="#badges" role="tab" data-toggle="tab">Badges</a></li>
            ## %endif
            </ul>

        </div><!-- end #obTabHead -->
        <div class="tab-content" >
            <div class="m-t-md tab-pane active" id="quicktasks">
                <ul class="ob-widget-list"> <!-- start onboarding -->
                    <div id="obGoToProject">
                        <osf-ob-goto params="data: nodes"></osf-ob-goto>
                    </div>
                    <div id="obCreateProject">
                        <osf-ob-create params="data: nodes"></osf-ob-create>
                    </div>

                    % if not disk_saving_mode:
                    <div id="obRegisterProject">
                        <osf-ob-register params="data: nodes"></osf-ob-register>
                    </div>
                    <div id="obUploader">
                        <osf-ob-uploader params="data: nodes"></osf-ob-uploader>
                    </div>
                    % endif
                </ul> <!-- end onboarding -->
            </div>
            <div class="m-t-md tab-pane" id="watchlist">
                <%include file="log_list.mako" args="scripted=False"/>
            </div>
            ## %if 'badges' in addons_enabled:
                ## <%include file="dashboard_badges.mako"/>
            ## %endif
        </div><!-- end .tab-content -->
    </div><!-- end col -->
</div><!-- end row -->
%if 'badges' in addons_enabled:
    <div class="row">
        <div class="col-sm-5">
            <div class="page-header">
              <button class="btn btn-primary pull-right" id="newBadge" type="button">New Badge</button>
                <h3>Your Badges</h3>
            </div>
            <div mod-meta='{
                     "tpl": "../addons/badges/templates/dashboard_badges.mako",
                     "uri": "/api/v1/dashboard/get_badges/",
                     "replace": true
                }'></div>
        </div>
        <div class="col-sm-5">
            <div class="page-header">
                <h3>Badges You've Awarded</h3>
            </div>
        </div><!-- end col -->
    </div><!-- end row -->
%endif
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/dashboard-page.css">
</%def>

<%def name="javascript_bottom()">
<script>
    window.contextVars = $.extend(true, {}, window.contextVars, {
        currentUser: {
            'id': '${user_id}'
        }
    });
</script>
<script src=${"/static/public/js/dashboard-page.js" | webpack_asset}></script>

</%def>
