<%inherit file="base.mako"/>
<%def name="title()">Project Statistics</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>
    <%
        piwik_url = 'http://localhost:8888/index.php?module=Widgetize&action=iframe&moduleToWidgetize=Dashboard&actionToWidgetize=index&idSite={site_id}&period=week&date=yesterday&disableLink=1&token_auth={auth_token}'.format(
            auth_token=node['piwik_credentials']['auth_token'],
            site_id=node['piwik_credentials']['site_id'],
        )
        %>
    <iframe seamless="seamless" width="100%" height='600' src="${ piwik_url }">

    </iframe>
</%def>
