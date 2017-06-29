<%inherit file="base.mako"/>
<%def name="title()">Home</%def>

<%def name="content_wrap()">
    <div class="watermarked">
        ## Maintenance alert
        <div style="margin-bottom: 0px" class="alert alert-warning" role="alert">
            <strong>Notice:</strong> File operations may be temporarily unavailable. We are experiencing issues with our downstream file storage provider and are actively working to
            resolve the issue. No data have been lost. Thank you for your patience.
        </div>
        % if maintenance:
        <div id="maintenance" class="scripted alert alert-info alert-dismissible" role="alert">
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span></button>
            <strong>Notice:</strong> The site will undergo maintenance between
            <span id="maintenanceTime"></span>.
            Thank you for your patience.
        </div>
        % endif
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
