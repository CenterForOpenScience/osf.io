<%inherit file="base.mako"/>
<%def name="title()">${ meeting['name'] }</%def>

<%def name="nav()">
    <%namespace name="nav_helper" file="nav.mako" />
    ${nav_helper.nav(service_name='MEETINGS', service_url='/meetings/', service_support_url='https://openscience.zendesk.com/hc/en-us/categories/360001550933')}
</%def>

<%def name="content()">
    <%include file="public/pages/meeting_body.mako" />
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
</%def>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script type="text/javascript">
        window.contextVars = window.contextVars || {};
        window.contextVars.meetingData = ${ data | sjson, n };

        $('#addLink').on('click', function(e) {
            e.preventDefault();
            $('#submit').slideToggle();
        })

    </script>
    <script src=${"/static/public/js/conference-page.js" | webpack_asset}></script>
</%def>
