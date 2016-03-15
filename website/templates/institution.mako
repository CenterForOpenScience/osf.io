<%inherit file="base.mako"/>
<%def name="title()">Institution</%def>

<%def name="container_class()">container-xxl</%def>

<%def name="content()">
% if disk_saving_mode:
    <div class="alert alert-info"><strong>NOTICE: </strong>Forks, registrations, and uploads will be temporarily disabled while the OSF undergoes a hardware upgrade. These features will return shortly. Thank you for your patience.</div>
% endif
    <div id="inst">
<div class="dashboard-header">
    <div class="row" style="text-align: center">
        <div class="col-sm-2"></div>
        <div class="col-sm-3"><img class="img-circle" height="110" width="110" src=${ logo_path }></div>
        <div class="col-sm-3">
            <h2>${ name }</h2>
            % if description:
                <h4><small class="hidden-sm">${description}</small></h4>
            % endif
        </div>
        <div class="col-sm-2"></div>
    </div>
</div>
  <div id="fileBrowser" class="fileBrowser clearfix" >
    <div class="spinner-loading-wrapper">
       <div class="logo-spin logo-lg"></div>
       <p class="m-t-sm fg-load-message"> Loading projects...  </p>
    </div>
  </div>
    </div>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/dashboard.css">
    <link rel="stylesheet" href="/static/css/pages/dashboard-page.css">
</%def>

<%def name="javascript_bottom()">
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            institution: {
                name: ${ name | sjson, n},
                id: ${ id | sjson, n},
                logoPath: ${ logo_path | sjson, n},
            },
            currentUser: {
                'id': '${user_id}'
            }
        });
    </script>
    ${parent.javascript_bottom()}
    <script src="${"/static/public/js/institution-page.js" | webpack_asset}"></script>
</%def>
