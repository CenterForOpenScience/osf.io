<% import json %>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Statistics</%def>
<script type="text/javascript" src="http://code.highcharts.com/highcharts.js"></script>


<div class="row">
    <input type="text" id="datepicker" class="form-control">
    <button class="btn btn-default" id="datepicker-btn">Select Date</button>
</div>
<div class="row">
    <div class="col-md-12">
        <div class="panel panel-default">
             <div class="panel-heading clearfix">
                <h3 class="panel-title">Statistics for ${node['title']}</h3>
            </div>
            <div class="panel-body">
                <div class="piwikChart"></div>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Components </h3>
            </div>
            <div class="panel-body">
                <table id="componentStats" class="table"></table>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Files</h3>
            </div>
            <div class="panel-body">
                <table id="fileStats" class="table"></table>
            </div>
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