<%inherit file="base.mako"/>
<%def name="title()">Dashboard</%def>

<%def name="content()">

${ spa(spa_config) }

<!--
<div class="row">

  <div class="col-sm-7">
        <div>
          <h3>Projects </h3>
            <hr />
        </div>

        <div class="project-organizer" id="projectOrganizerScope">
            <div id="project-grid">
                <div class="spinner-loading-wrapper">
                    <div class="logo-spin logo-lg"></div>
                     <p class="m-t-sm fg-load-message"> Loading projects...  </p>
                </div>
            </div>
        </div>
    </div>
    <div class="col-sm-5">
        <div class="p-b-xs m-t-lg m-b-xs" id="obTabHead">
            <ul class="nav nav-tabs" role="tablist">
            <li class="active"><a href="#quicktasks" role="tab" data-toggle="tab">Quick Tasks</a></li>
            <li><a href="#watchlist" role="tab" data-toggle="tab">Watchlist</a></li>   
            </ul>

        </div>
        <div class="tab-content" >
            <div class="m-t-md tab-pane active" id="quicktasks">
                <ul class="ob-widget-list">
                    <div id="obGoToProject">
                      Goto Project Onboarder
                    </div>
                    <div id="obCreateProject">
                      Create Project Onboarder,
                    </div>
                    <div id="obRegisterProject">
                      Register Project Onboarder
                    </div>
                    <div id="obUploader">
                      Upload File Onboarder
                    </div>
                </ul>
                
            </div>
            <div class="m-t-md tab-pane" id="watchlist">
              Watched Projects Logs
            </div>
        </div>
    </div>
</div>
-->
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


<%def name="spa(data)">
<%
tmpl = data['template_lookup'].get_template(data['root_template']).render(**data)
%>   
${tmpl | n}
</%def>
