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
% if not node.get('piwik_site_id'):
        <img src="/static/img/no_analytics.png">
% else:
    % if not node.get('is_public'):
        <div class='alert alert-warning alert-dismissable'>
            <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
            <strong>Note:</strong> Usage statistics are collected only for public resources.
        </div>
    % endif
    <iframe style="overflow-y:scroll;border:none;" width="100%" height='600' src="${ piwik_url }"></iframe>
% endif

