<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Analytics</%def>

<div class="page-header  visible-xs">
    <h2 class="text-300">Analytics</h2>
</div>

<div class="row m-lg">
    <div class="col-sm-4">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Visits</h3>
            </div>
            <div id="visits" class="panel-body">
            </div>
        </div>
    </div>
    <div class="col-sm-4">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Top Referrers</h3>
            </div>
            <div id="topReferrers" class="panel-body">
            </div>
        </div>
    </div>
    <div class="col-sm-4">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Visits by Server Time</h3>
            </div>
            <div id="serverTimeVisits" class="panel-body">
            </div>
        </div>
    </div>
</div>


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

% if not piwik_host or not node['piwik_site_id']:
    <div class="row m-lg">
        <div class="col-xs-12 text-center">
            <img class="img-responsive center" src="/static/img/no_analytics.png">
        </div>
    </div>
% else:
    % if not node['is_public']:
        <div class='alert alert-warning'>
            <strong>Note:</strong> Usage statistics are collected only for public resources.
        </div>
    % endif
    <iframe style="overflow-y:scroll;border:none;" width="100%" height="600" src="${ piwik_url }"></iframe>
% endif

%if keen_project_id:
        <script>
            window.contextVars = $.extend(true, {}, window.contextVars, {
                keenReadKey: ${node['keenio_read_key'] | sjson, n},
            })
        </script>
%endif

<%def name="javascript_bottom()">
${parent.javascript_bottom()}
    <script src="${'/static/public/js/statistics-page.js' | webpack_asset}"></script>

</%def>




