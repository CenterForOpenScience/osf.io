<% import json %>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Analytics</%def>

<<<<<<< HEAD
<div id="statistics" class="scripted">
    <div class="row">
        <div class="col-xs-6">
            <input type="text" id="datePickerField" class="hidden">
            <input type="text" id="endDatePickerField" class="hidden">
            <button class="btn btn-default" type="button" id="datePickerButton" data-toggle="collapse" data-target="#calendarRow"
                    aria-expanded="false" aria-controls="calendarRow" data-bind="html: dateButtonHTML"></button>
        </div>
        <div class="col-xs-6">
            <div class="btn-group pull-right">
                <button id="changeStatsBtn" type="button" class="btn btn-default dropdown-toggle" data-bind="html: optionsButtonHTML"
                        data-toggle="dropdown" aria-expanded="false">
                </button>
                <ul class="dropdown-menu" role="menu" data-bind="foreach: dataTypeOptions">
                    <li><a href="#" data-bind="text: $data, click: $parent.changeDataType"></a></li>
                </ul>
            </div>
        </div>
    </div>
    <div class="collapse" id="calendarRow">
        <div class="row">
            <div class="col-xs-6">
                <label class="radio-inline">
                    <input type="radio" name="dateOption" id="date"checked>
                    Date
                </label>
                <label class="radio-inline">
                    <input type="radio" name="dateOption" id="dateRange">
                    Date Range
                </label>
            </div>
        </div>
        <div class="row form-inline">
            <div class="col-sm-12">
                <input type="text" class="form-control" id="startPickerField" placeholder="Select a date">
                <input type="text" class="form-control hidden" id="endPickerField" placeholder="Select end date">
            </div>
        </div>
    </div>
    <div class="row p-t-md">
        <div class="col-md-12">
            <div class="panel panel-default">
                 <div class="panel-heading clearfix">
                    <h3 class="panel-title" data-bind="text: dataType() + ' for ' + nodeTitle"></h3>
                </div>
                <div class="panel-body">
                    <div class="piwikChart"></div>
                </div>
            </div>
        </div>
    </div>
    <div class="row">
        <div class="col-md-6">
            <div class="panel panel-default">
                <div class="panel-heading clearfix">
                    <h3 class="panel-title">Public Components of ${node['title']} </h3>
                </div>
                <div class="panel-body">
                    <!-- ko if: children().length -->
                    <table id="componentStats" class="table">
                        <thead>
                            <th class="col-xs-3">Title</th>
                            <th class="col-xs-3" data-bind="text: dataType"></th>
                            <th class="col-xs-6"></th>
                        </thead>
                        <tbody data-bind="foreach: renderChildren">
                            <td><a data-bind="attr: {href: '/' + guid}, text: title"></a></td>
                            <td data-bind="text: total"></td>
                            <td data-bind="attr: {id: guid + 'Spark'}, sparkline: $data"></td>
                        </tbody>
                    </table>
                    <!-- /ko -->
                    <!-- ko if: renderChildren().length < children().length -->
                    <div class="text-center">
                        <a data-bind="click: incrementChildrenLimit">Load more...</a>
                    </div>
                    <!-- /ko -->
                    <!-- ko ifnot: children().length -->
                    <h4>This ${node['category'].lower()} does not have any components or none of the components are public.</h4>
                    <!-- /ko -->
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="panel panel-default">
                <div class="panel-heading clearfix">
                    <h3 class="panel-title">Files of ${node['title']}</h3>
                </div>
                <div class="panel-body">
                    <!-- ko if: files().length -->
                    <table id="fileStats" class="table">
                        <thead>
                            <th class="col-xs-3">Title</th>
                            <th class="col-xs-3" data-bind="text: dataType"></th>
                            <th class="col-xs-6 "></th>
                        </thead>
                        <tbody data-bind="foreach: renderFiles">
                            <td><a data-bind="attr: {href: '/' + guid}, text: title"></a></td>
                            <td data-bind="text: total"></td>
                            <td data-bind="attr: {id: guid + 'Spark'}, sparkline: $data"></td>
                        </tbody>
                    </table>
                    <!-- /ko -->
                    <!-- ko if: renderFiles().length < files().length -->
                    <div class="text-center">
                        <a data-bind="click: incrementFilesLimit">Load more...</a>
                    </div>
                    <!-- /ko -->
                    <!-- ko ifnot: files().length -->
                    <h4>This ${node['category'].lower()} does not have any files or none of the files have been visited.</h4>
                    <!-- /ko -->
                </div>
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

<%def name="javascript_bottom()">

${parent.javascript_bottom()}
<script type="text/javascript" src=${"/static/public/js/statistics-page.js" | webpack_asset}></script>

</%def>
