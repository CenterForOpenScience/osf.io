<%inherit file="base.mako"/>
<%def name="title()">${ meeting['name'] } Presentations</%def>

<%def name="content()">
    <%include file="public/pages/meeting_body.mako" />
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="${asset_base_url}/static/vendor/bower_components/hgrid/dist/hgrid.min.css" />
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = window.contextVars || {};
        window.contextVars.meetingData = ${data};

        $('#addLink').on('click', function(e) {
            e.preventDefault();
            $('#submit').slideToggle();
        })

    </script>
    <script src="${asset_base_url}${'/static/public/js/conference-page.js' | webpack_asset}"></script>
</%def>
