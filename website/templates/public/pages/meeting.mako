<%inherit file="base.mako"/>
<%def name="title()">${ meeting['name'] }</%def>

<%def name="nav()">
    <%namespace name="nav_helper" file="nav.mako" />
    ${nav_helper.nav(service_name='MEETINGS', service_url='/meetings/', service_support_url='http://help.osf.io/m/meetings/')}
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
        window.contextVars.currentPageNumber = ${ current_page_number | sjson, n };
        window.contextVars.totalPages = ${ total_pages | sjson, n };
        window.contextVars.q = ${ q | sjson, n };
        window.contextVars.sort = ${ sort | sjson, n };
        window.contextVars.hasPrevious = ${page.has_previous() | sjson, n };
        window.contextVars.hasNext = ${page.has_next() | sjson, n };
        window.contextVars.meetingData = ${ data | sjson, n };

        $('#addLink').on('click', function(e) {
            e.preventDefault();
            $('#submit').slideToggle();
        })

    </script>
    <script src=${"/static/public/js/conference-page.js" | webpack_asset}></script>
</%def>
