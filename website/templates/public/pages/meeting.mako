<%inherit file="base.mako"/>
<%def name="title()">${ meeting['name'] } Presentations</%def>

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
        window.contextVars.meetingData = ${data};

        $('#addLink').on('click', function(e) {
            e.preventDefault();
            $('#submit').slideToggle();
        })

    </script>
    <script src=${"/static/public/js/conference-page.js" | webpack_asset}></script>
</%def>
