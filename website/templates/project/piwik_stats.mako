<% import json %>
<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Statistics</%def>

<div id="statistics" class="scripted row">
    <div class="col-xs-6 col-md-6">
        <input type="text" id="datePickerField" class="hidden">
        <input type="text" id="endDatePickerField" class="hidden">
        <button class="btn btn-default" id="datePickerButton" data-placement="bottom" data-bind="html: dateButtonHTML"></button>
    </div>
    <div class="col-xs-6 col-md-6">
        <div class="btn-group pull-right">
            <button id="changeStatsBtn" type="button" class="btn btn-default dropdown-toggle" data-bind="html: optionsButtonHTML"
                    data-toggle="dropdown" aria-expanded="false">
            </button>
            <ul class="dropdown-menu" role="menu" data-bind="foreach: dataTypeOptions">
                <li><a href="#" data-bind="text: $data, click: $parent.changeDataType"></a></li>
            </ul>
        </div>
    </div>
    <div class="col-xs-12 col-md-12">
        <div class="panel panel-default">
             <div class="panel-heading clearfix">
                <h3 class="panel-title">Statistics for ${node['title']}</h3>
            </div>
            <div class="panel-body">
                <div class="piwikChart"></div>
            </div>
        </div>
    </div>
    <div class="col-xs-12 col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Components </h3>
            </div>
            <div class="panel-body">
                <!-- ko if: children().length -->
                <table id="componentStats" class="table scripted">
                    <thead>
                        <th style="min-width: 150px;">Title</th>
                        <th data-bind="text: 'Total ' + dataType()"></th>
                        <th style="width: 50%;">Over Time</th>
                    </thead>
                    <tbody data-bind="foreach: renderChildren">
                        <td><a data-bind="attr: {href: '/' + guid}, text: title"></a></td>
                        <td data-bind="text: total"></td>
                        <td data-bind="attr: {id: guid + 'Spark'}"></td>
                    </tbody>
                </table>
                <!-- /ko -->
                <!-- ko if: renderChildren().length < children().length -->
                <button data-bind="click: function() {renderMore('children')}" class=" scripted btn btn-default">Load more...</button>
                <!-- /ko -->
                <!-- ko ifnot: children().length -->
                <h4 class="scripted">This ${node['category'].lower()} does not have any components.</h4>
                <!-- /ko -->
            </div>
        </div>
    </div>
    <div class="col-xs-12 col-md-6">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Files</h3>
            </div>
            <div class="panel-body">
                <!-- ko if: files().length -->
                <table id="fileStats" class="table scripted">
                    <thead>
                        <th style="min-width: 150px;">Title</th>
                        <th data-bind="text: dataType"></th>
                        <th style="width: 50%;">Over Time</th>
                    </thead>
                    <tbody data-bind="foreach: renderFiles">
                        <td><a data-bind="attr: {href: '/' + guid}, text: title"></a></td>
                        <td data-bind="text: total"></td>
                        <td data-bind="attr: {id: guid + 'Spark'}"></td>
                    </tbody>
                </table>
                <!-- /ko -->
                <!-- ko if: renderFiles().length < files().length -->
                <button data-bind="click: function() {renderMore()}" class=" scripted btn btn-default">Load more...</button>
                <!-- /ko -->
                <!-- ko ifnot: files().length -->
                <h4 class="scripted">This ${node['category'].lower()} does not have any visited files.</h4>
                <!-- /ko -->
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
    <script type="text/javascript" src=${"/static/public/js/piwikStats-page.js" | webpack_asset}></script>

</%def>
