<%inherit file="base.mako"/>
<%def name="title()">Home</%def>

<%def name="content_wrap()">
    <div class="watermarked">
        ## Maintenance alerts
        % for maintenance in maintenance_states:
            ${maintenance}
            <div id="maintenance-${maintenance['_id']}" class="scripted alert alert-info alert-dismissible" role="alert">
                <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                    <span aria-hidden="true">&times;</span></button>
                <strong>Notice:</strong> The site will undergo maintenance between
                <span id="maintenance-time-${maintenance['_id']}"></span>.
                Thank you for your patience.
            </div>
        % endfor
        ## End Maintenance alert
        <div class="home-page-alert">
            % if status:
                ${self.alert()}
            % endif
        </div>
    </div><!-- end watermarked -->

    ${self.content()}
</%def>


<%def name="content()">

    <div id="osfHome"></div>

</%def>

<%def name="stylesheets()">
  <link rel="stylesheet" href="/static/css/pages/home-page.css">
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = $.extend(true, {}, window.contextVars, {
            dashboardInstitutions: ${ dashboard_institutions | sjson, n},
        });
    </script>
    <script src=${"/static/public/js/home-page.js" | webpack_asset}></script>
</%def>
