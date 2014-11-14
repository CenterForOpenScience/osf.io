<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Statistics</%def>

<%
    if user['is_contributor']:
        token = user.get('piwik_token', 'anonymous')
    else:
        token = 'anonymous'

    if node.get('piwik_site_id'):
        piwik_url = '{host}index.php?module=Widgetize&action=iframe&moduleToWidgetize=Dashboard&actionToWidgetize=index&idSite={site_id}&period=day&date=today&disableLink=1&token_auth={auth_token}'.format(
            host=piwik_host,
            auth_token=token,
            site_id=node['piwik_site_id'],
        )
%>

% if node['is_public']:
    % if node['piwik_site_id']:
        <iframe style="overflow-y:scroll;border:none;" width="100%" height='600' src="${ piwik_url }"></iframe>
    % else:
        <div>Setting up your analytics dashboard. Please check back in a few minutes.</div>
    % endif
% else:
    <div class='alert alert-warning'>
        <strong>Note:</strong> Usage statistics are collected only for public resources.
    </div>
    <img src="/static/img/no_analytics.png">
% endif
