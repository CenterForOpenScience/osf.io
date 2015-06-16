<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Statistics</%def>
<script type="text/javascript" src="http://code.highcharts.com/highcharts.js"></script>

<div class="row">
    <div class="col-md-4">
        <div class="panel panel-default">
             <div class="panel-heading">
                <h3 class="panel-title">C3 Pageviews</h3>
            </div>
            <div class="panel-body piwikChart"></div>
        </div>
    </div>
    <div class="col-md-4">
        <div class="panel panel-default">
            <div class="panel-heading">
                <h3 class="panel-title">HighCharts Pageviews</h3>
            </div>
            <div class="panel-body highchart"></div>
        </div>
    </div>
</div>

<script type="text/javascript" src=${"/static/public/js/piwikStats-page.js" | webpack_asset}></script>