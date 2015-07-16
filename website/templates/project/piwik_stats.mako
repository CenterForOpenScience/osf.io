<% import json %>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Statistics</%def>
<script type="text/javascript" src="http://code.highcharts.com/highcharts.js"></script>

<div class="row">
    <div class="col-md-12">
        <div class="panel panel-default">
             <div class="panel-heading">
                <h3 class="panel-title">C3 Pageviews</h3>
            </div>
            <div class="panel-body piwikChart"></div>
        </div>
    </div>
</div>

% if node['files']:
<script>
    var nodeFiles = ${json.dumps(node['files'])};
</script>
% else:
<script>
    var nodeFiles = [];
</script>
% endif

<script type="text/javascript" src=${"/static/public/js/piwikStats-page.js" | webpack_asset}></script>