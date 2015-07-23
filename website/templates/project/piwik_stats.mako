<% import json %>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Statistics</%def>

<div class="row">
    <div class="col-md-3">
        <input type="text" id="datepicker" class="hidden">
        <button type="button" class="btn btn-default" id="datepickerButton">Select Date</button>
        <button type="button" class="btn btn-default" id="rangeButton">Select Range</button>
    </div>
    <div class="col-md-3" id="rangeDiv">
        <input type="text" id="startPicker">
        <input type="text" id="endPicker">
    </div>
    <div class="col-md-6">
        <div class="btn-group pull-right">
            <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-expanded="false">
                Statistics <span class="fa fa-caret-down"></span>
            </button>
            <ul class="dropdown-menu" role="menu">
                <li><a href="#">Visits</a></li>
                <li><a href="#">Page Views</a></li>
                <li><a href="#">Unique Page Views</a></li>
                <li><a href="#">Unique Visitors</a></li>
            </ul>
        </div>
    </div>
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