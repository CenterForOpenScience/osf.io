<%inherit file="base.mako"/>
<%def name="title()">Institution</%def>

<%def name="container_class()">container-xxl</%def>

<%def name="content()">
% if disk_saving_mode:
    <div class="alert alert-info"><strong>NOTICE: </strong>Forks, registrations, and uploads will be temporarily disabled while the OSF undergoes a hardware upgrade. These features will return shortly. Thank you for your patience.</div>
% endif
    <div id="inst">
        <div class="dashboard-header dashboard-header-institution">
            <div class="row" style="text-align: center">
                % if banner_path:
                    <div class="col-sm-6 col-sm-offset-3"><img alt="${ name }" style="max-height: 100%; max-width: 100%" src="${ banner_path }"></div>
                % else:
                    <div class="col-sm-3 col-sm-offset-2"><img alt="${ name }" class="img-circle" height="110px" width="110px" src=${ logo_path }></div>
                    <div class="col-sm-3">
                        <h2>${ name }</h2>
                    </div>
                % endif
            </div>
            % if description:
                <div class="row" style="text-align: center">
                    <div class="text-muted text-smaller">${description | n}</div>
                </div>
            % endif
        </div>
      <div id="fileBrowser" class="dashboard clearfix" >
        <div class="ball-scale text-center m-v-xl"><div></div></div>
      </div>
    </div>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/my-projects.css">
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
